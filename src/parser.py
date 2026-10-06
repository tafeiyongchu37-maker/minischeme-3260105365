"""语法分析：词列表 -> 表达式（嵌套的 Python 数据结构）。

Scheme 的程序和数据是同一种形状（S-表达式），所以 parser 只做一件事：
把括号和 `'` 还原成嵌套结构，不做任何语义判断。

    (define (f x) (* x x))
       -> [Symbol('define'), [Symbol('f'), Symbol('x')],
           [Symbol('*'), Symbol('x'), Symbol('x')]]

表达式用 Python list 表示"括号表达式"，具体值直接用对应 Python 对象。
`

(quote x)` 会被展开成 [Symbol('quote'), x]（spec §4.1）。
"""

from lexer import tokenize
from scheme_types import Symbol


class ParseError(Exception):
    """语法错误（例如括号不匹配）。"""


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def next(self):
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def parse_program(self):
        """解析整个程序：返回顶层表达式列表。"""
        exprs = []
        while self.peek()[0] != "eof":
            exprs.append(self.parse_expr())
        return exprs

    def parse_expr(self):
        kind, value = self.next()

        if kind == "(":
            return self._parse_list()
        if kind == ")":
            raise ParseError("出现了多余的右括号 )")
        if kind == "'":
            # 'x 是 (quote x) 的简写
            return [Symbol("quote"), self.parse_expr()]
        if kind == "eof":
            raise ParseError("表达式还没写完，文件就结束了")
        # int / float / bool / string / symbol 本身就是表达式
        return value

    def _parse_list(self):
        items = []
        while True:
            kind, _ = self.peek()
            if kind == ")":
                self.next()
                return items
            if kind == "eof":
                raise ParseError("缺少与之配对的右括号 )")
            items.append(self.parse_expr())


def parse(text):
    """解析一段程序文本，返回顶层表达式列表。"""
    return _Parser(tokenize(text)).parse_program()


def parse_all(text):
    """parse 的别名，语义更明确：一次解析一批顶层表达式。"""
    return parse(text)
