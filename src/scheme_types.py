"""mini-Scheme 的值类型定义。

解释器流水线：文本 --lexer--> 词 --parser--> 表达式 --evaluator--> 值 --printer--> 文本

本模块只负责"值"的表示，是其他所有模块的共同语言：
    * Symbol   符号（变量名 / 操作符名）
    * Pair     点对，列表就是用点对链表示的
    * nil      空表 ()
    * int / float / bool / str  对应整数、浮点数、布尔、字符串
    * Procedure 内置过程与用户定义的闭包（定义在 evaluator 中）

之所以不用 Python 的 list 表示 Scheme 列表，是因为本题要求区分
"真列表" 与 "点对"（`(cons 1 2)` 要打印成 `(1 . 2)`），
用显式的点对链可以天然地表达这一点，也让打印与 equal? 的实现更直白。
"""


class Symbol(str):
    """符号类型。

    继承 str 只是为了让符号在打印/调试时更自然，但必须在比较时
    与字符串区分开：`(equal? 'a "a")` 必须为 #f（见 spec §11）。
    """

    __slots__ = ()

    def __repr__(self):
        return "'" + str(self)


class Pair:
    """点对：列表的基本单元。(1 2 3) 即 Pair(1, Pair(2, Pair(3, nil)))。"""

    __slots__ = ("car", "cdr")

    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def __repr__(self):
        return "<Pair>"


class _Nil:
    """空表 ()。用单例表示，这样 `(eq? '() '())` 天然为 #t。"""

    __slots__ = ()
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "()"


nil = _Nil()

#: 真 / 假。只有 #f 为假（spec §9）。
TRUE = True
FALSE = False


class BuiltinProcedure:
    """内置过程，例如 +、car、display。fn 是一个 Python 可调用对象。"""

    __slots__ = ("name", "fn")

    def __init__(self, name, fn):
        self.name = name
        self.fn = fn

    def __repr__(self):
        return "#<procedure:%s>" % self.name


class Procedure:
    """用户定义的过程（闭包）。

    保存 params（形参名列表）、body（函数体表达式列表）以及
    env（**定义时**的环境）——保存定义时环境正是词法作用域/闭包的关键。
    """

    __slots__ = ("params", "body", "env", "name")

    def __init__(self, params, body, env, name=None):
        self.params = params
        self.body = body
        self.env = env
        self.name = name

    def __repr__(self):
        return "#<procedure:%s>" % (self.name or "lambda")


def is_procedure(value):
    """判断一个值是不是过程（内置或用户定义）。"""
    return isinstance(value, (BuiltinProcedure, Procedure))


def is_true(value):
    """Scheme 真值判断：只有 #f 为假，0、()、"" 都是真。"""
    return value is not FALSE


def scheme_list(*items):
    """把若干 Python 值打包成 Scheme 列表（点对链）。"""
    result = nil
    for item in reversed(items):
        result = Pair(item, result)
    return result


def scheme_list_to_py(value):
    """把真列表转成 Python list；不是真列表时抛 ValueError。"""
    out = []
    while isinstance(value, Pair):
        out.append(value.car)
        value = value.cdr
    if value is not nil:
        raise ValueError("not a proper list")
    return out
