"""函数与代码对象探针 —— 查看 PyFunctionObject 和 PyCodeObject 的内部。

演示内容：
  - 函数对象的 __name__, __code__, __defaults__ 等属性
  - 代码对象的 co_argcount, co_varnames, co_consts, co_flags 等字段
  - 闭包如何通过 cell 对象捕获外部变量
  - 默认参数的共享陷阱
"""

import dis


def show_code_info(func) -> None:
    """打印一个函数的代码对象详细信息。"""
    code = func.__code__
    print(f"\n--- {func.__name__} 的代码对象 ---")
    print(f"  co_argcount:       {code.co_argcount}")
    print(f"  co_posonlyargcount: {code.co_posonlyargcount}")
    print(f"  co_kwonlyargcount: {code.co_kwonlyargcount}")
    print(f"  co_nlocals:        {code.co_nlocals}")
    print(f"  co_stacksize:      {code.co_stacksize}")
    print(f"  co_flags:          {code.co_flags} (0b{code.co_flags:010b})")
    print(f"  co_names:          {code.co_names}")
    print(f"  co_varnames:       {code.co_varnames}")
    print(f"  co_consts:         {code.co_consts}")
    print(f"  co_filename:       {code.co_filename}")
    print(f"  co_name:           {code.co_name}")
    print(f"  co_firstlineno:    {code.co_firstlineno}")
    print(f"  co_freevars:       {code.co_freevars}")
    print(f"  co_cellvars:       {code.co_cellvars}")
    print(f"  #free vars:        {len(code.co_freevars)}")
    print(f"  #cell vars:        {len(code.co_cellvars)}")

    # 解析 co_flags
    flags = code.co_flags
    flag_names = [
        (0x0001, "CO_OPTIMIZED"),
        (0x0002, "CO_NEWLOCALS"),
        (0x0004, "CO_VARARGS"),
        (0x0008, "CO_VARKEYWORDS"),
        (0x0010, "CO_NESTED"),
        (0x0020, "CO_GENERATOR"),
        (0x0080, "CO_COROUTINE"),
        (0x0200, "CO_ASYNC_GENERATOR"),
        (0x8000000, "CO_METHOD"),
    ]
    for bit, name in flag_names:
        if flags & bit:
            print(f"    -> {name}")


def main() -> None:
    print("=" * 60)
    print("函数与代码对象探针")
    print("=" * 60)

    # ── 1. 一个简单函数 ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 简单函数")
    print("=" * 60)

    def add(a, b):
        return a + b

    print(f"\nadd 的类型: {type(add)}")
    print(f"add.__name__: {add.__name__}")
    print(f"add.__code__: {add.__code__}")

    show_code_info(add)

    print("\n--- 字节码反汇编 ---")
    dis.dis(add)

    # ── 2. 有默认参数的函数 ─────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 默认参数")
    print("=" * 60)

    def with_default(x, lst=[], name="hello"):
        return x, lst, name

    print(f"\nfunc_defaults: {with_default.__defaults__}")
    print(f"func_defaults 地址: {id(with_default.__defaults__)}")

    # 默认参数的"陷阱"
    print("\n--- 默认参数陷阱 ---")

    def append_to(item, target=[]):
        target.append(item)
        return target

    print(f"第一次: {append_to(1)}")
    print(f"第二次: {append_to(2)}")
    print(f"第三次: {append_to(3)}")
    print(f"默认参数对象 id: {id(append_to.__defaults__[0])}")
    print("（每次调用都操作同一个列表！）")

    # ── 3. 闭包 ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 闭包与 cell 对象")
    print("=" * 60)

    def outer(x):
        def inner(y):
            return x + y
        return inner

    f = outer(10)
    print(f"\nouter(10) 返回的函数: {f}")
    print(f"f(5) = {f(5)}")

    print(f"\ninner.__closure__: {f.__closure__}")
    if f.__closure__:
        for i, cell in enumerate(f.__closure__):
            print(f"  cell[{i}]: {cell} = {cell.cell_contents}")

    print(f"\ninner.__code__.co_freevars: {f.__code__.co_freevars}")
    print(f"inner.__code__.co_cellvars: {f.__code__.co_cellvars}")

    show_code_info(f)

    # ── 4. 嵌套作用域的 cell 变量 ──────────────────────────
    print("\n" + "=" * 60)
    print("4. 多层闭包")
    print("=" * 60)

    def multiplier(factor):
        def apply(value):
            return value * factor
        return apply

    double = multiplier(2)
    triple = multiplier(3)

    print(f"double(5) = {double(5)}")
    print(f"triple(5) = {triple(5)}")

    c0 = double.__closure__[0].cell_contents
    c1 = triple.__closure__[0].cell_contents
    print(f"\ndouble.__closure__[0].cell_contents = {c0}")
    print(f"triple.__closure__[0].cell_contents = {c1}")
    print("两个函数共享同一份代码对象，但有不同的闭包！")

    # ── 5. 各种函数类型的 co_flags ──────────────────────────
    print("\n" + "=" * 60)
    print("5. 不同函数类型的 co_flags")
    print("=" * 60)

    # 普通函数
    def normal(): pass
    print(f"\n普通函数 co_flags: {normal.__code__.co_flags}")

    # 生成器函数
    def gen():
        yield 1
    print(f"生成器函数 co_flags: {gen.__code__.co_flags} "
          f"(has GENERATOR: {bool(gen.__code__.co_flags & 0x0020)})")

    # async 函数
    async def async_func():
        pass
    print(f"async 函数 co_flags: {async_func.__code__.co_flags} "
          f"(has COROUTINE: {bool(async_func.__code__.co_flags & 0x0080)})")

    # 有 *args 和 **kwargs 的函数
    def varargs(*args, **kwargs): pass
    print(f"varargs 函数 co_flags: {varargs.__code__.co_flags} "
          f"(has VARARGS: {bool(varargs.__code__.co_flags & 0x0004)}, "
          f"has VARKEYWORDS: {bool(varargs.__code__.co_flags & 0x0008)})")

    # ── 6. 使用 __code__ 属性验证代码对象不变性 ────────────
    print("\n" + "=" * 60)
    print("6. 代码对象不变性")
    print("=" * 60)

    def a(): pass
    def b(): pass
    print(f"两个空函数的代码对象相同：{a.__code__ is b.__code__}")
    print("（因为它们的字节码完全一样，CPython 复用了代码对象）")


if __name__ == "__main__":
    main()
