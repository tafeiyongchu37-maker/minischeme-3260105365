"""内置库：spec §5 的全部内置过程，放进初始环境（spec §9）。

内置过程与特殊形式的区别：内置过程的**参数先全部求值**再调用，
所以这里拿到的都是值，不需要关心语法。

实现上有三条容易踩的坑，均在注释中标注：
    * 整数相除得整数商，且负数向零截断（不能直接用 Python 的 //）
    * `=` 等比较是链式比较
    * `eq?` 对复合数据比同一性，`equal?` 才是结构比较
"""

import sys

from environment import Environment, SchemeError
from printer import to_display_raw
from scheme_types import (
    BuiltinProcedure,
    Pair,
    Symbol,
    is_procedure,
    nil,
    scheme_list,
    scheme_list_to_py,
)


def _is_number(value):
    # 注意：Python 里 bool 是 int 的子类，必须先排除布尔
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_number(value, name):
    if not _is_number(value):
        raise SchemeError("%s 需要数字，得到 %s" % (name, to_display_raw(value)))
    return value


def _require_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemeError("%s 需要整数，得到 %s" % (name, to_display_raw(value)))
    return value


def _require_pair(value, name):
    if not isinstance(value, Pair):
        raise SchemeError("%s 需要非空点对，得到 %s" % (name, to_display_raw(value)))
    return value


def _truncate_div(a, b):
    """整数除法：商向零截断（Python 的 // 是向下取整，负数会差 1）。"""
    if b == 0:
        raise SchemeError("除数不能为 0")
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _all_numbers(args):
    return all(_is_number(a) for a in args)


# ---------------------------------------------------------------- 算术

def _add(args):
    total = 0
    for a in args:
        _require_number(a, "+")
        total += a
    return total


def _sub(args):
    if not args:
        raise SchemeError("- 至少需要一个参数")
    for a in args:
        _require_number(a, "-")
    if len(args) == 1:
        return -args[0]
    total = args[0]
    for a in args[1:]:
        total -= a
    return total


def _mul(args):
    total = 1
    for a in args:
        _require_number(a, "*")
        total *= a
    return total


def _div(args):
    if not args:
        raise SchemeError("/ 至少需要一个参数")
    for a in args:
        _require_number(a, "/")
    if len(args) == 1:
        # 单参数取倒数，结果是浮点（spec §5）
        if args[0] == 0:
            raise SchemeError("除数不能为 0")
        return 1 / args[0]
    if all(isinstance(a, int) for a in args):
        total = args[0]
        for a in args[1:]:
            total = _truncate_div(total, a)
        return total
    total = args[0]
    for a in args[1:]:
        if a == 0:
            raise SchemeError("除数不能为 0")
        total = total / a
    return total


def _modulo(args):
    a = _require_int(args[0], "modulo")
    b = _require_int(args[1], "modulo")
    if b == 0:
        raise SchemeError("modulo 的除数不能为 0")
    return a % b


def _quotient(args):
    a = _require_int(args[0], "quotient")
    b = _require_int(args[1], "quotient")
    return _truncate_div(a, b)


def _expt(args):
    base = _require_number(args[0], "expt")
    power = _require_number(args[1], "expt")
    result = base ** power
    # 数学上应为整数的结果不要带上浮点尾巴
    if isinstance(result, float) and result.is_integer():
        return int(result)
    return result


def _abs(args):
    return abs(_require_number(args[0], "abs"))


# ---------------------------------------------------------------- 比较

def _compare(op, args, name, ordered):
    for a in args:
        if not _is_number(a) and not isinstance(a, Symbol):
            raise SchemeError("%s 只能比较数字或符号" % name)
    for left, right in zip(args, args[1:]):
        # 符号之间只能比相等；大小比较仍然交给 Python 的同类型比较
        if isinstance(left, Symbol) or isinstance(right, Symbol):
            if ordered:
                raise SchemeError("%s 不能比较符号的大小" % name)
            if str(left) != str(right):
                return False
            continue
        if not op(left, right):
            return False
    return True


# ---------------------------------------------------------------- 列表

def _cons(args):
    return Pair(args[0], args[1])


def _car(args):
    return _require_pair(args[0], "car").car


def _cdr(args):
    return _require_pair(args[0], "cdr").cdr


def _list(args):
    return scheme_list(*args)


def _length(args):
    items = scheme_list_to_py(args[0])
    return len(items)


def _append(args):
    """拼接若干列表：最后一个参数可以不是列表（Scheme 的标准语义）。"""
    if not args:
        return nil
    result_tail = args[-1]
    for lst in reversed(args[:-1]):
        items = scheme_list_to_py(lst)
        for item in reversed(items):
            result_tail = Pair(item, result_tail)
    return result_tail


def _list_p(args):
    """list?：真列表要求每一层 cdr 都以 () 收尾。"""
    value = args[0]
    while isinstance(value, Pair):
        value = value.cdr
    return value is nil


# ---------------------------------------------------------------- 谓词

def _eq(args):
    """eq?：符号/数字/布尔按值比较，复合数据比同一性（spec §5 / §11）。"""
    a, b = args[0], args[1]
    if isinstance(a, Pair) or isinstance(b, Pair):
        return a is b
    if isinstance(a, Symbol) and isinstance(b, Symbol):
        return str(a) == str(b)
    if _is_number(a) and _is_number(b):
        return a == b
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, str) and isinstance(b, str):
        return a is b
    return a is b


def _equal(args):
    """equal?：递归的结构相等。"""
    return _equal_values(args[0], args[1])


def _equal_values(a, b):
    if a is b:
        return True
    if isinstance(a, Symbol) or isinstance(b, Symbol):
        # 符号只和同名符号相等，不与字符串相等
        return isinstance(a, Symbol) and isinstance(b, Symbol) and str(a) == str(b)
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a is b
    if _is_number(a) and _is_number(b):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if isinstance(a, Pair) and isinstance(b, Pair):
        return _equal_values(a.car, b.car) and _equal_values(a.cdr, b.cdr)
    return False


def _number_p(args):
    return _is_number(args[0])


def _boolean_p(args):
    return isinstance(args[0], bool)


def _symbol_p(args):
    return isinstance(args[0], Symbol)


def _string_p(args):
    # 注意：Symbol 是 str 的子类，必须先排除
    return isinstance(args[0], str) and not isinstance(args[0], Symbol)


def _procedure_p(args):
    return is_procedure(args[0])


def _zero_p(args):
    return _require_number(args[0], "zero?") == 0


def _even_p(args):
    return _require_int(args[0], "even?") % 2 == 0


def _odd_p(args):
    return _require_int(args[0], "odd?") % 2 != 0


# ---------------------------------------------------------------- 输出

def _display(args):
    """打印一个值，字符串不带引号，不换行；结果无值所以不打印。"""
    sys.stdout.write(to_display_raw(args[0]))
    sys.stdout.flush()
    return None


def _newline(args):
    sys.stdout.write("\n")
    sys.stdout.flush()
    return None


def _not(args):
    return args[0] is False


# ---------------------------------------------------------------- 注册表

#: 名字 -> Python 实现。用表驱动而不是一长串 if，方便阅读和扩展。
_BUILTINS = {
    "+": _add,
    "-": _sub,
    "*": _mul,
    "/": _div,
    "modulo": _modulo,
    "quotient": _quotient,
    "expt": _expt,
    "abs": _abs,
    "=": lambda args: _compare(lambda a, b: a == b, args, "=", False),
    "<": lambda args: _compare(lambda a, b: a < b, args, "<", True),
    ">": lambda args: _compare(lambda a, b: a > b, args, ">", True),
    "<=": lambda args: _compare(lambda a, b: a <= b, args, "<=", True),
    ">=": lambda args: _compare(lambda a, b: a >= b, args, ">=", True),
    "not": _not,
    "cons": _cons,
    "car": _car,
    "cdr": _cdr,
    "list": _list,
    "length": _length,
    "append": _append,
    "null?": lambda args: args[0] is nil,
    "pair?": lambda args: isinstance(args[0], Pair),
    "list?": _list_p,
    "number?": _number_p,
    "boolean?": _boolean_p,
    "symbol?": _symbol_p,
    "string?": _string_p,
    "procedure?": _procedure_p,
    "zero?": _zero_p,
    "even?": _even_p,
    "odd?": _odd_p,
    "eq?": _eq,
    "equal?": _equal,
    "display": _display,
    "newline": _newline,
}


def make_global_env():
    """构造初始环境：只有内置过程，没有任何用户变量（spec §2）。"""
    env = Environment()
    for name, fn in _BUILTINS.items():
        env.define(Symbol(name), BuiltinProcedure(name, fn))
    return env
