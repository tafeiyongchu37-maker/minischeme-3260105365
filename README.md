# mini-Scheme 解释器（2026 纳新题 3.3.3 程序部分）

这是一个从零实现的 mini-Scheme 解释器，语言规范见仓库里的 [spec.md](spec.md)。
按题目要求，它通过了自测评分器的全部 **12 组验收用例**。

- 学号：3260105365
- 姓名：姚响
- 入口：`src/main.py`
- 实现语言：Python 3（仅用标准库，没有第三方依赖）

## 1. 怎么运行

```bash
# 求值一个或多个 .scm 文件（多个文件共享同一个全局环境）
python3 src/main.py example/01_arithmetic.scm

# 没有参数时从标准输入读取
echo '(+ 1 2)' | python3 src/main.py

# 跑自测评分器（12 组用例，难度递增）
python3 autograder.pyz python3 src/main.py

# 只跑其中一组
python3 autograder.pyz python3 src/main.py --case=006
```

## 2. 模块划分（流水线）

我按 README 建议的流水线把解释器拆成了职责单一的小模块，每个模块只做一件事：

| 文件 | 职责 | 对应流水线的一步 |
| --- | --- | --- |
| `src/scheme_types.py` | 值的表示：Symbol / Pair（点对链）/ nil / 过程对象 | 所有模块的共同语言 |
| `src/lexer.py` | 程序文本 → 词（token）列表 | 读 |
| `src/parser.py` | 词 → 表达式（嵌套结构），处理括号与 `'` 简写 | 读 |
| `src/printer.py` | 值 → 文本（真列表 / 点对 / 字符串转义） | 打印 |
| `src/environment.py` | 变量绑定表 + 指向外层环境的指针 | 算 |
| `src/primitives.py` | spec §5 的全部内置过程，放进初始环境 | 算 |
| `src/evaluator.py` | evaluate / apply 与所有特殊形式 | 算（心脏） |
| `src/main.py` | 读文件、逐行打印结果，即入口 | 入口 |

```
程序文本 ──lexer──▶ 词 ──parser──▶ 表达式 ──evaluator──▶ 值 ──printer──▶ 结果
```

## 3. 自测结果

`python3 autograder.pyz python3 src/main.py` 的实际输出：

```
  PASS  001_arithmetic
  PASS  002_comparisons
  PASS  003_booleans
  PASS  004_conditionals
  PASS  005_define_lambda
  PASS  006_recursion
  PASS  007_lists
  PASS  008_closures
  PASS  009_higher_order
  PASS  010_let_begin
  PASS  011_io
  PASS  012_predicates

12 passed, 0 failed
```

`example/` 里的 6 个示例程序也逐一跑过，输出与每行注释标注的期望值一致，例如：

```
$ python3 src/main.py example/05_lists.scm
1
(2 3)
(1 2 3)
(1 . 2)
(1 2 3)
4
(1 2 3 4)
map
(1 4 9 16)
```

## 4. 实现中真正花时间的几个点

1. **quote 的数据必须是点对链。** 一开始 parser 用 Python 的 list 表示表达式，`'(1 2 3)` 直接返回了这个 list，结果 `(car '(1 2 3))` 报错。改成在 quote 时把嵌套 list 递归转成 `Pair` 链，这样引用数据和 `cons` 造出来的数据才是同一种东西，打印、`car/cdr`、`equal?` 才都自洽。
2. **整数除法要往零截断。** Python 的 `//` 是向下取整，`-7 // 2 == -4`，而 spec 要求 `(quotient -7 2)` → `-3`。所以自己写了截断除法。
3. **`and` / `or` 必须短路。** spec 里直接用 `(and #f (/ 1 0))` 来考这一点，先求值全部表达式再判断的实现会直接崩掉。
4. **`eq?` 与 `equal?` 不是一回事。** `(eq? '(1) '(1))` 必须是 `#f`（比同一性），`(equal? '(1 2 3) (list 1 2 3))` 必须是 `#t`（比结构）；另外 Python 里 `True == 1`、`Symbol` 是 `str` 的子类，稍不注意就会把 `#t` 和 `1`、符号 `a` 和字符串 `"a"` 判成相等。
5. **`define` 的结果是被定义的符号名。** 顶层会把它打印出来（`(define pi 3)` 输出 `pi`），第一版漏了这一点，输出少了好几行。

详细的试错过程见 [调试记录.md](调试记录.md)。

## 5. 目录结构

```
3260105365_姚响_程序部分/
├── README.md             本文件：用途、运行方式、完成情况
├── 调试记录.md           遇到问题和解决的记录
├── spec.md               题目给出的语言规范（仓库自带，未修改）
├── autograder.pyz        题目给出的自测评分器（仓库自带，未修改）
├── example/              题目给出的 6 个示例程序
└── src/                  我写的解释器
    ├── main.py
    ├── lexer.py
    ├── parser.py
    ├── evaluator.py
    ├── environment.py
    ├── primitives.py
    ├── printer.py
    └── scheme_types.py
```

## 6. AI 使用说明

- 我通读了 `spec.md`，把每个小节的要求整理成一份清单，再逐个实现；遇到不确定的行为（例如 `cond` 子句没有表达式时返回什么）以 spec 原文为准。
- 用 AI 辅助完成了代码骨架与逐条对照 spec 的自测用例；解释器的结构（模块怎么拆、evaluate/apply 怎么互相调用）是我按 README 的提示确定的。
- 报错时的定位过程记录在 `调试记录.md` 里，每一步都自己跑过一遍确认。
