"""求值器：表达式 -> 值（解释器的心脏）。

核心是 evaluate 与 apply 两个**互相递归**的函数：

    evaluate(expr, env)
        符号        -> 去环境里查它的值
        字面量      -> 原样返回（整数/浮点/布尔/字符串）
        括号表达式  -> 特殊形式按各自规则处理（spec §4）
                       其余都是函数调用：先求值操作符与全部实参，再交给 apply

    apply(proc, args)
        内置过程 -> 直接调用 Python 实现
        用户闭包 -> 新建一层环境把实参绑到形参上（parent 指向**定义时**的环境），
                    再回到 evaluate 依次求值函数体

evaluate 遇到函数调用就调 apply，apply 执行函数体又调回 evaluate——
想通这个循环，解释器就完成了一半，剩下的都是逐个特殊形式照着 spec 抄。
"""

from environment import Environment, SchemeError, ensure_symbol
from scheme_types import (
    BuiltinProcedure,
    Pair,
    Procedure,
    Symbol,
    is_procedure,
    nil,
    scheme_list_to_py,
)

#: 特殊形式的名字集合，用于快速判断
_SPECIAL_FORMS = frozenset(
    ["quote", "if", "cond", "and", "or", "define", "lambda", "let", "begin"]
)


def evaluate(expr, env):
    """求值一个表达式，返回它的值。"""
    # 1) 具体值：数字、字符串、布尔、空表等自求值
    if isinstance(expr, Symbol):
        return env.lookup(expr)
    if isinstance(expr, Pair):
        # quote 展开后可能直接是数据，这里统一按表达式列表处理
        expr = _to_expr_list(expr)
    if not isinstance(expr, list):
        return expr  # int / float / bool / str 原样返回

    if not expr:
        raise SchemeError("空表达式 () 不能求值")

    head = expr[0]

    # 2) 特殊形式：自己决定怎么求值
    if isinstance(head, Symbol) and str(head) in _SPECIAL_FORMS:
        return _eval_special(str(head), expr[1:], env)

    # 3) 函数调用：先求值操作符和全部实参，再 apply
    proc = evaluate(head, env)
    args = [evaluate(item, env) for item in expr[1:]]
    return apply_procedure(proc, args)


def apply_procedure(proc, args):
    """调用一个过程。"""
    if isinstance(proc, BuiltinProcedure):
        return proc.fn(args)

    if isinstance(proc, Procedure):
        if len(args) != len(proc.params):
            raise SchemeError(
                "%s 需要 %d 个参数，实际给了 %d 个"
                % (proc.name or "lambda", len(proc.params), len(args))
            )
        # 新建一层环境：parent 指向定义时的环境（闭包的关键）
        call_env = proc.env.child()
        for name, value in zip(proc.params, args):
            call_env.define(name, value)
        return eval_sequence(proc.body, call_env)

    raise SchemeError("这不是一个可以调用的过程：%r" % (proc,))


def eval_sequence(exprs, env):
    """按 begin 语义依次求值，返回最后一个的值；空序列返回 None。"""
    result = None
    for expr in exprs:
        result = evaluate(expr, env)
    return result


def _to_expr_list(pair):
    """把 parser 之外的 Pair 结构（来自内存中的表达式）转成 list。"""
    return scheme_list_to_py(pair)


# ---------------------------------------------------------------- 特殊形式

def _eval_special(name, operands, env):
    handler = _SPECIAL_HANDLERS[name]
    return handler(operands, env)


def _sf_quote(operands, env):
    if len(operands) != 1:
        raise SchemeError("quote 只接受一个参数")
    # parser 用 Python list 表示 S-表达式，而运行时数据必须是点对链，
    # 否则 '(1 2 3) 会被 car/cdr 当成"不是点对"，也无法用 cons 与它拼接
    return _to_data(operands[0])


def _to_data(value):
    """把 parser 产出的嵌套 list 转成与 cons 一致的运行期数据（点对链）。"""
    if isinstance(value, list):
        result = nil
        for item in reversed(value):
            result = Pair(_to_data(item), result)
        return result
    return value


def _sf_if(operands, env):
    if len(operands) < 2 or len(operands) > 3:
        raise SchemeError("if 的形式是 (if 测试 真分支 假分支?)")
    test = evaluate(operands[0], env)
    if test is not False:
        return evaluate(operands[1], env)
    if len(operands) == 3:
        return evaluate(operands[2], env)
    return None  # 省略假分支且测试为假 -> 无值


def _sf_cond(operands, env):
    for clause in operands:
        if not isinstance(clause, list) or not clause:
            raise SchemeError("cond 的每个子句都要写成 (测试 表达式...)")
        test_expr = clause[0]
        # else 子句：无条件命中
        if isinstance(test_expr, Symbol) and str(test_expr) == "else":
            return eval_sequence(clause[1:], env)
        test_value = evaluate(test_expr, env)
        if test_value is not False:
            if len(clause) == 1:
                return test_value  # 子句里没有表达式时返回测试值本身
            return eval_sequence(clause[1:], env)
    return None  # 全部不匹配


def _sf_and(operands, env):
    result = True
    for expr in operands:
        result = evaluate(expr, env)
        if result is False:
            return False  # 短路：后面的表达式不执行
    return result


def _sf_or(operands, env):
    for expr in operands:
        result = evaluate(expr, env)
        if result is not False:
            return result  # 短路：后面的表达式不执行
    return False


def _sf_define(operands, env):
    if not operands:
        raise SchemeError("define 至少需要一个参数")

    target = operands[0]

    # 写法一：(define 名 表达式)
    if isinstance(target, Symbol):
        if len(operands) != 2:
            raise SchemeError("(define 名 表达式) 只能有两个参数")
        value = evaluate(operands[1], env)
        if isinstance(value, Procedure) and value.name is None:
            value.name = str(target)  # 给闭包起个名字，方便报错信息
        env.define(target, value)
        return target  # define 的结果是被定义的符号名（顶层会打印）

    # 写法二：(define (函数名 参数...) 体...) —— 等价于 lambda 的简写
    if isinstance(target, list) and target:
        func_name = ensure_symbol(target[0], "define")
        params = [ensure_symbol(p, "define") for p in target[1:]]
        body = operands[1:]
        if not body:
            raise SchemeError("函数体不能为空")
        proc = Procedure(params, body, env, name=str(func_name))
        env.define(func_name, proc)
        return func_name

    raise SchemeError("define 的名字必须是符号或 (名 参数...) 形式")


def _sf_lambda(operands, env):
    if len(operands) < 2:
        raise SchemeError("lambda 的形式是 (lambda (参数...) 体...)")
    params_expr = operands[0]
    if not isinstance(params_expr, list):
        raise SchemeError("lambda 的参数表必须是列表（不支持可变参数）")
    params = [ensure_symbol(p, "lambda") for p in params_expr]
    return Procedure(params, operands[1:], env)


def _sf_let(operands, env):
    if not operands:
        raise SchemeError("let 的形式是 (let ((名 表达式)...) 体...)")
    bindings = operands[0]
    if not isinstance(bindings, list):
        raise SchemeError("let 的绑定表必须是列表")

    # 先在**外层环境**把每个绑定表达式求值完（并行绑定，绑定之间互不可见）
    evaluated = []
    for binding in bindings:
        if not isinstance(binding, list) or len(binding) != 2:
            raise SchemeError("let 的绑定要写成 (名 表达式)")
        name = ensure_symbol(binding[0], "let")
        evaluated.append((name, evaluate(binding[1], env)))

    let_env = env.child()
    for name, value in evaluated:
        let_env.define(name, value)
    return eval_sequence(operands[1:], let_env)


def _sf_begin(operands, env):
    return eval_sequence(operands, env)


_SPECIAL_HANDLERS = {
    "quote": _sf_quote,
    "if": _sf_if,
    "cond": _sf_cond,
    "and": _sf_and,
    "or": _sf_or,
    "define": _sf_define,
    "lambda": _sf_lambda,
    "let": _sf_let,
    "begin": _sf_begin,
}
