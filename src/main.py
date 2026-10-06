#!/usr/bin/env python3
"""mini-Scheme 解释器入口（评分器调用的就是这个文件）。

用法：
    python3 src/main.py file1.scm [file2.scm ...]     # 依次求值各文件
    python3 src/main.py                               # 从标准输入读取

约定（spec §2）：
    * 每个顶层表达式求值后独占一行打印它的值
    * 值为 None（如 display、newline 的结果）时不打印
    * 多个文件共享同一个全局环境
    * 每个测试用例在独立进程中运行，初始环境为空（只有内置过程）
"""

import os
import sys

# 允许直接以 `python3 src/main.py` 运行：把本文件所在目录加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from primitives import make_global_env  # noqa: E402
from environment import SchemeError  # noqa: E402
from evaluator import evaluate  # noqa: E402
from lexer import LexError  # noqa: E402
from parser import ParseError, parse  # noqa: E402
from printer import to_display  # noqa: E402


def run_source(text, env):
    """求值一段程序文本，按 spec 的约定打印每个顶层表达式的结果。"""
    for expr in parse(text):
        value = evaluate(expr, env)
        if value is None:
            continue  # 无值不打印
        sys.stdout.write(to_display(value) + "\n")
    sys.stdout.flush()


def read_source(path):
    """读入源文件。UTF-8 优先，失败时退回系统默认编码以增强鲁棒性。"""
    with open(path, "rb") as handle:
        raw = handle.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode(sys.getdefaultencoding(), errors="replace")


def main(argv):
    env = make_global_env()

    if len(argv) > 1:
        for path in argv[1:]:
            try:
                source = read_source(path)
            except OSError as error:
                sys.stderr.write("无法读取文件 %s：%s\n" % (path, error))
                return 1
            run_source(source, env)
        return 0

    # 没有参数：从标准输入读取，并逐个表达式边读边打印
    source = sys.stdin.read()
    run_source(source, env)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except (SchemeError, ParseError, LexError) as error:
        # 明确报出解释器层面的错误，而不是打印 Python 堆栈（便于对照 spec 排错）
        sys.stderr.write("解释器错误：%s\n" % error)
        sys.exit(1)
