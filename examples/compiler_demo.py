"""Compiler 探针 — 观察代码对象和字节码生成。

演示内容：
  - compile() 创建代码对象
  - 代码对象属性
  - 不同函数生成不同 co_stacksize
"""

import dis
import types


def show_code_info(code: types.CodeType) -> None:
    """打印代码对象的关键信息。"""
    print(f"  co_argcount:   {code.co_argcount}")
    print(f"  co_nlocals:    {code.co_nlocals}")
    print(f"  co_stacksize:  {code.co_stacksize}")
    print(f"  co_flags:      {code.co_flags}")
    print(f"  co_consts:     {code.co_consts}")
    print(f"  co_varnames:   {code.co_varnames}")
    print(f"  co_names:      {code.co_names}")
    print(f"  co_filename:   {code.co_filename}")
    print(f"  co_name:       {code.co_name}")


def main() -> None:
    print("=" * 60)
    print("Compiler 探针")
    print("=" * 60)

    # ── 1. 表达式代码对象 ──────────────────────────────────
    print("\n1. 表达式 compile")
    code1 = compile("x + 42", "<expr>", "eval")
    print(dis.dis(code1))

    # ── 2. 语句代码对象 ──────────────────────────────────
    print("\n2. 语句 compile")
    code2 = compile("x = 42; y = x * 2", "<stmt>", "exec")
    show_code_info(code2)
    dis.dis(code2)

    # ── 3. 函数代码对象 ──────────────────────────────────
    print("\n3. 函数代码对象")
    def f(a, b):
        return a + b
    show_code_info(f.__code__)
    dis.dis(f)

    # ── 4. 闭包代码对象 ──────────────────────────────────
    print("\n4. 闭包代码对象")
    def make_counter():
        x = 0
        def counter():
            nonlocal x
            x += 1
            return x
        return counter
    counter = make_counter()
    print("  outer co_freevars:", make_counter.__code__.co_freevars)
    print("  inner co_freevars:", counter.__code__.co_freevars)
    print("  inner co_cellvars:", counter.__code__.co_cellvars)

    # ── 5. co_stacksize 对比 ──────────────────────────────
    print("\n5. co_stacksize 对比")
    def simple():
        return 42
    def nested_expr():
        return (1 + 2) * (3 + 4) - 5
    print(f"  simple:      co_stacksize={simple.__code__.co_stacksize}")
    print(f"  nested_expr: co_stacksize={nested_expr.__code__.co_stacksize}")


if __name__ == "__main__":
    main()
