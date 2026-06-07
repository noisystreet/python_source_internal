"""迭代器与生成器探针 —— 观察迭代器协议和生成器内部状态。

演示内容：
  - 迭代器协议：__iter__ / __next__ / tp_iter / tp_iternext
  - 序列迭代器内部的下标变化
  - for 循环的字节码
  - 生成器的挂起/恢复
  - send / throw / close 方法
  - yield from 委托
"""

import dis
import types


def show_iterator_internals(it) -> None:
    """用 ctypes 读取序列迭代器的内部字段。"""
    import ctypes

    it_index = ctypes.c_ssize_t.from_address(id(it) + 16)  # 偏移 16: it_index
    it_seq_ptr = ctypes.c_void_p.from_address(id(it) + 24)  # 偏移 24: it_seq
    seq_addr = it_seq_ptr.value

    print(f"  迭代器地址:         {id(it):#x}")
    print(f"  it_index:           {it_index.value}")
    if seq_addr is not None:
        print(f"  it_seq (指针):      {seq_addr:#x}")
    else:
        print("  it_seq:             NULL (已耗尽)")


def main() -> None:
    print("=" * 60)
    print("迭代器与生成器探针")
    print("=" * 60)

    # ── 1. 序列迭代器内部结构 ───────────────────────────────
    print("\n" + "=" * 60)
    print("1. 序列迭代器内部")
    print("=" * 60)

    lst = [10, 20, 30, 40]
    it = iter(lst)

    print(f"\n列表: {lst}")
    print(f"迭代器类型: {type(it)}")
    print(f"迭代器类型名: {type(it).__name__}")

    show_iterator_internals(it)

    print("\n依次迭代:")
    for _ in range(4):
        val = next(it)
        show_iterator_internals(it)
        print(f"  -> next() = {val:>3}, it_index now: "
              f"{ctypes.c_ssize_t.from_address(id(it) + 16).value}")

    # 迭代器耗尽
    print("\n迭代器耗尽:")
    try:
        next(it)
    except StopIteration:
        show_iterator_internals(it)
        print("  -> StopIteration (it_seq = NULL)")

    # ── 2. for 循环的字节码 ────────────────────────────────
    print("\n" + "=" * 60)
    print("2. for 循环的字节码")
    print("=" * 60)

    def simple_for():
        lst = [1, 2, 3]
        total = 0
        for x in lst:
            total += x
        return total

    dis.dis(simple_for)

    # ── 3. 生成器的帧状态 ──────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 生成器的生命周期")
    print("=" * 60)

    def gen_func(n):
        """一个简单的生成器，从 0 数到 n-1。"""
        i = 0
        while i < n:
            yield i
            i += 1

    gen = gen_func(3)
    print(f"\n生成器对象: {gen}")
    print(f"生成器类型: {type(gen)}")
    print(f"gi_frame (生成器是否持有帧): {gen.gi_frame is not None}")
    print(f"gi_running: {gen.gi_running}")
    print(f"gi_suspended: {gen.gi_suspended}")

    values = []
    for val in gen:
        values.append(val)
        print(f"  next() = {val}, 帧存在: {gen.gi_frame is not None}")

    print(f"\n生成器耗尽后 gi_frame: {gen.gi_frame}")
    # 注意：gi_frame 是 None 因为帧已被回收

    # ── 4. send 方法 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("4. send 方法")
    print("=" * 60)

    def echo():
        """yield 接收外部传入的值。"""
        received = 0
        while True:
            received = yield received
            if received is None:
                received = 0

    g = echo()
    print(f"首次: next(g) = {next(g)}")
    print(f"send(42): g.send(42) = {g.send(42)}")
    print(f"send(100): g.send(100) = {g.send(100)}")
    print(f"send(-1): g.send(-1) = {g.send(-1)}")

    # 关闭
    g.close()
    print("\nclose() 后")
    try:
        next(g)
    except StopIteration:
        print("  next(g) -> StopIteration")

    # ── 5. throw 方法 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. throw 方法")
    print("=" * 60)

    def catch_exception():
        """生成器内部捕获异常。"""
        try:
            yield "正常运行"
        except ValueError as e:
            yield f"捕获到 ValueError: {e}"
        yield "继续执行"

    g2 = catch_exception()
    print(f"  next(g2) = {next(g2)}")
    print(f"  g2.throw(ValueError('test')) = {g2.throw(ValueError('test'))}")
    print(f"  next(g2) = {next(g2)}")

    # ── 6. yield from ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("6. yield from 委托")
    print("=" * 60)

    def sub_gen():
        yield "A"
        yield "B"
        yield "C"

    def main_gen():
        yield "START"
        yield from sub_gen()
        yield "END"

    print("main_gen() 的输出:")
    for val in main_gen():
        print(f"  {val}")

    # ── 7. 生成器表达式 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("7. 生成器表达式")
    print("=" * 60)

    gen_expr = (x * 2 for x in range(5))
    print(f"生成器表达式类型: {type(gen_expr)}")
    print(f"是生成器? {isinstance(gen_expr, types.GeneratorType)}")
    print(f"值: {list(gen_expr)}")

    # 查看生成器表达式的代码对象
    gen_expr2 = (x * 2 for x in range(3))
    print("\n生成器表达式的 gi_code (字节码):")
    print(f"  {gen_expr2.gi_code}")
    print(f"  co_name = {gen_expr2.gi_code.co_name}")


if __name__ == "__main__":
    import ctypes  # noqa: F401
    main()
