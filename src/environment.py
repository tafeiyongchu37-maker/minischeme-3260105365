"""环境：变量绑定表 + 指向外层环境的指针（spec §4.6 / §9）。

环境就是一条链：查找变量时先看当前层，找不到再顺着 parent 往外找，
一直找都没有就报"未定义的变量"。lambda 调用时会新建一层环境并让
parent 指向**函数定义时**的环境，这就是词法作用域与闭包的实现基础。
"""

from scheme_types import Symbol


class SchemeError(Exception):
    """解释器意义上的错误（未定义变量、类型不符等）。"""


class Environment:
    """一层作用域。"""

    __slots__ = ("bindings", "parent")

    def __init__(self, parent=None):
        self.bindings = {}
        self.parent = parent

    def define(self, name, value):
        """在当前层建立（或覆盖）绑定——define 用的就是它。"""
        self.bindings[name] = value
        return value

    def lookup(self, name):
        """沿环境链查找变量的值。"""
        env = self
        while env is not None:
            if name in env.bindings:
                return env.bindings[name]
            env = env.parent
        raise SchemeError("未定义的变量：%s" % name)

    def set(self, name, value):
        """修改已经存在的绑定（供 define 覆盖同名变量时使用）。"""
        env = self
        while env is not None:
            if name in env.bindings:
                env.bindings[name] = value
                return value
            env = env.parent
        self.bindings[name] = value
        return value

    def child(self):
        """新建一层子环境，用于函数调用 / let。"""
        return Environment(parent=self)


def ensure_symbol(value, where):
    """把绑定名检查成 Symbol，避免把 `(define 1 2)` 之类的写法放进来。"""
    if not isinstance(value, Symbol):
        raise SchemeError("%s 需要一个符号作为名字，得到 %r" % (where, value))
    return value
