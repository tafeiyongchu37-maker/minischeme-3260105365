"""打印：值 -> 文本（spec §8）。

    * 整数 42 / 浮点 0.5
    * 布尔 #t / #f
    * 符号 foo
    * 字符串带引号，并且把换行、制表符等打印成 \\n \\t 转义形式
    * 真列表 (1 2 3)、点对 (1 . 2)、空表 ()
    * 过程 #<procedure>

`display` 与顶层打印的区别只有一个：display 输出字符串时不带引号，
所以用 write_string=False 表示"给人看的写法"。
"""

from scheme_types import Pair, Symbol, is_procedure, nil


def to_display(value):
    """顶级打印用的文本（字符串带引号，符合 spec §8 的表格）。"""
    return _write(value, write_string=True)


def to_display_raw(value):
    """display 用的文本（字符串不带引号、不转义）。"""
    return _write(value, write_string=False)


def _write(value, write_string):
    if value is True:
        return "#t"
    if value is False:
        return "#f"
    if value is nil:
        return "()"
    if isinstance(value, Symbol):
        return str(value)
    if isinstance(value, str):  # 注意：Symbol 是 str 的子类，必须放在后面判断
        return _write_string(value) if write_string else value
    if isinstance(value, float):
        return _format_float(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Pair):
        return _write_pair(value, write_string)
    if is_procedure(value):
        return "#<procedure>"
    if value is None:
        # 无值（例如 display 的结果）：调用方约定不打印
        return ""
    return str(value)


def _format_float(value):
    """浮点尽量打印成 0.5 这样的短形式，必要时才用科学计数法。"""
    if value == int(value) and abs(value) < 1e16:
        return "%.1f" % value
    return repr(value)


def _write_string(text):
    """带引号的字符串写法：换行、制表符、引号、反斜杠都要转义。"""
    out = ['"']
    for ch in text:
        if ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _write_pair(pair, write_string):
    """点对链的打印：能凑成真列表就写 (1 2 3)，否则写 (1 . 2)。"""
    parts = ["("]
    current = pair
    while isinstance(current, Pair):
        parts.append(_write(current.car, write_string))
        current = current.cdr
        if current is nil:
            parts.append(")")
            return "".join(parts)
        if isinstance(current, Pair):
            parts.append(" ")
            continue
        # 非法结尾（Improper list），用点号写法
        parts.append(" . ")
        parts.append(_write(current, write_string))
        parts.append(")")
        return "".join(parts)
    # 理论上不会走到这里
    parts.append(")")
    return "".join(parts)
