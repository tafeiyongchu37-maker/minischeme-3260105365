"""词法分析：程序文本 -> 词（token）列表。

token 用 tuple 表示，第一个元素是种类，方便 parser 做模式匹配：
    ("(", None) (" )" 同)     括号
    ("'", None)               引用简写
    ("int", 42) ("float", 0.5) ("bool", True) ("string", "hi")
    ("symbol", Symbol("+"))   符号（含 #t/#f 以外的标识符与操作符）
    ("eof", None)             输入结束哨兵

处理规则（spec §3）：
    * `;` 到行尾是注释；字符串内部的 `;` 不算注释
    * 字符串支持 \\n \\t \\" \\\\ 转义
    * 括号是最简单的分隔符，`(+ 1 2)` 与 `( + 1 2 )` 等价
    * `'x` 产生两个词：quote 简写 + 符号
"""

from scheme_types import Symbol

#: 字符串转义表
_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}

#: 无需按名字查找即可识别的字面量（注释掉的 #f/#t 除外）
_SPECIALS = {"#t": True, "#f": False}

_DELIMITERS = set("()' \t\r\n")


class LexError(Exception):
    """词法错误（例如字符串没有闭合）。"""


def tokenize(text):
    """把文本切成词列表，末尾总有 ("eof", None)。"""
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]

        # 1) 空白
        if ch in " \t\r\n":
            i += 1
            continue

        # 2) 注释：; 到行尾
        if ch == ";":
            while i < n and text[i] != "\n":
                i += 1
            continue

        # 3) 括号与引用简写
        if ch == "(" or ch == ")":
            tokens.append((ch, None))
            i += 1
            continue
        if ch == "'":
            tokens.append(("'", None))
            i += 1
            continue

        # 4) 字符串
        if ch == '"':
            i += 1
            buf = []
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    nxt = text[i + 1]
                    buf.append(_ESCAPES.get(nxt, nxt))  # 未知转义按字面处理
                    i += 2
                else:
                    buf.append(text[i])
                    i += 1
            if i >= n:
                raise LexError("字符串缺少收尾的双引号")
            i += 1  # 跳过收尾引号
            tokens.append(("string", "".join(buf)))
            continue

        # 5) 原子：读到下一个分隔符为止
        start = i
        while i < n and text[i] not in _DELIMITERS:
            i += 1
        atom = text[start:i]
        tokens.append(_classify(atom))

    tokens.append(("eof", None))
    return tokens


def _classify(atom):
    """把一个不含分隔符的片段归类成具体的词。"""
    if atom in _SPECIALS:
        return ("bool", _SPECIALS[atom])
    number = _parse_number(atom)
    if number is not None:
        return number
    return ("symbol", Symbol(atom))


def _parse_number(atom):
    """尝试把片段解析成整数或浮点数，失败返回 None（说明它是符号）。"""
    # 单独一个 + / - / ... 是符号而不是数字
    if atom in ("+", "-", ".", "..."):
        return None
    try:
        return ("int", int(atom, 10))
    except ValueError:
        pass
    try:
        return ("float", float(atom))
    except ValueError:
        return None
