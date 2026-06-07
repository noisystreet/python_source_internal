"""函数调用与 Vectorcall 协议探针。

演示内容：
  - 不同参数个数的调用
  - 调用链帧深度
  - 递归的帧开销
  - 方法调用 vs 函数调用
  - 关键字参数处理
"""

import dis


class FrameDepth:
    """模拟帧链追踪。"""
    def __init__(self):
        self.max_depth = 0
        self.current_depth = 0

    def enter(self, name: str):
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        print(f"  → {name} (帧深度: {self.current_depth})")

    def leave(self, name: str):
        print(f"  ← {name} (帧深度: {self.current_depth})")
        self.current_depth -= 1


def main() -> None:
    print("=" * 60)
    print("函数调用与 Vectorcall 协议探针")
    print("=" * 60)

    # ── 1. 不同参数个数的 CALL 指令 ────────────────────────
    print("\n" + "=" * 60)
    print("1. 不同参数个数的 CALL 指令")
    print("=" * 60)

    def f0(): pass
    def f1(a): pass
    def f2(a, b): pass
    def f3(a, b, c): pass
    def f_opt(a, b=10, c=20): pass

    def caller():
        f0()
        f1(1)
        f2(1, 2)
        f3(1, 2, 3)
        f_opt(1)

    print("  caller 函数的 CALL 指令:")
    for inst in dis.get_instructions(caller):
        if "CALL" in inst.opname:
            print(f"    {inst.opname:>20} -> {inst.argrepr}")

    # ── 2. 调用链帧深度 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 调用链帧深度")
    print("=" * 60)

    depth = FrameDepth()
    depth.enter("main")

    def c():
        depth.enter("c")
        depth.leave("c")
        return "c"

    def b():
        depth.enter("b")
        result = c()
        depth.leave("b")
        return result

    def a():
        depth.enter("a")
        result = b()
        depth.leave("a")
        return result

    a()
    depth.leave("main")
    print(f"\n  最大帧深度: {depth.max_depth}")

    # ── 3. 递归帧深度 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 递归的帧开销")
    print("=" * 60)

    def factorial(n):
        if n <= 1:
            return 1
        return n * factorial(n - 1)

    def trace_factorial(n, indent=0):
        prefix = "  " * indent
        print(f"{prefix}→ fact({n})")
        if n <= 1:
            print(f"{prefix}← fact({n}) = 1")
            return 1
        result = n * trace_factorial(n - 1, indent + 1)
        print(f"{prefix}← fact({n}) = {result}")
        return result

    print("  递归轨迹 (每个调用创建一个帧):")
    trace_factorial(5)

    # ── 4. 方法调用的反汇编 ────────────────────────────────
    print("\n" + "=" * 60)
    print("4. 方法调用 vs 函数调用")
    print("=" * 60)

    class MyClass:
        def method(self, x):
            return x * 2

    obj = MyClass()

    # 直接函数调用
    def call_function():
        MyClass.method(obj, 42)

    # 方法调用
    def call_method():
        obj.method(42)

    print("  MyClass.method(obj, 42):")
    dis.dis(call_function)
    print("\n  obj.method(42):")
    dis.dis(call_method)

    # ── 5. 关键字参数 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. 关键字参数的处理")
    print("=" * 60)

    def kw_func(a, b, c=0, d=0):
        return a + b + c + d

    def call_with_kw():
        return kw_func(1, 2, d=3, c=4)

    print("  kw_func(1, 2, d=3, c=4) 的字节码:")
    dis.dis(call_with_kw)

    # ── 6. 生成器调用的特殊处理 ────────────────────────────
    print("\n" + "=" * 60)
    print("6. 生成器函数的调用")
    print("=" * 60)

    def gen_func(n):
        yield from range(n)

    print("  gen_func(3) 的字节码 (注意 GENERATOR 标志):")
    dis.dis(gen_func)
    print(f"\n  co_flags & CO_GENERATOR: "
          f"{bool(gen_func.__code__.co_flags & 0x0020)}")
    print("  调用 gen_func(3): 不执行函数体，只创建生成器对象")


if __name__ == "__main__":
    main()
