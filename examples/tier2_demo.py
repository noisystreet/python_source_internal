"""Tier 2 优化器探针 — 观察热路径优化。

演示内容：
  - 热循环检测
  - 第一层与第二层性能差异
  - 循环代码的字节码结构
"""

import dis
import time


def main() -> None:
    print("=" * 60)
    print("Tier 2 优化器探针")
    print("=" * 60)

    # ── 1. 热循环的字节码结构 ──────────────────────────────
    print("\n" + "=" * 60)
    print("1. 循环体如何被 Tier 2 优化")
    print("=" * 60)

    def sum_range(n):
        total = 0
        for i in range(n):
            total += i
        return total

    print("  sum_range(n) 的循环部分字节码:")
    for inst in dis.get_instructions(sum_range):
        if inst.opname in ("FOR_ITER", "JUMP_BACKWARD", "BINARY_OP",
                           "LOAD_FAST", "STORE_FAST", "GET_ITER",
                           "LOAD_CONST"):
            print(f"    {inst.offset:>4} {inst.opname:>25} {inst.argrepr}")

    # ── 2. 增量 vs 一次完成的差距 ──────────────────────────
    print("\n" + "=" * 60)
    print("2. Tier 1 vs Tier 2 的概念对比")
    print("=" * 60)

    # Tier 1 模拟：逐条检查分发
    def tier1_simulate(data: list) -> int:
        result = 0
        for i in data:
            # 模拟每条指令的"检查分发"开销
            if isinstance(i, int):
                result += i
            elif isinstance(i, float):
                result += int(i)
            else:
                result += 0
        return result

    # Tier 2 模拟：假设已确认类型，直接执行
    def tier2_simulate(data: list) -> int:
        result = 0
        # 假设已确定所有元素都是 int
        for i in data:  # noqa: SIM110
            if isinstance(i, int):
                result += i
        return result

    data = list(range(1000))

    # 预热
    tier1_simulate(data)
    tier2_simulate(data)

    t1 = time.perf_counter()
    for _ in range(1000):
        tier1_simulate(data)
    t1_elapsed = time.perf_counter() - t1

    t2 = time.perf_counter()
    for _ in range(1000):
        tier2_simulate(data)
    t2_elapsed = time.perf_counter() - t2

    print(f"\n  Tier 1（通用检查）模拟: {t1_elapsed:.4f}s")
    print(f"  Tier 2（类型已确认）模拟: {t2_elapsed:.4f}s")
    print(f"  加速比: {t1_elapsed / t2_elapsed:.1f}x")

    # ── 3. 循环阈值 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 循环次数与优化触发")
    print("=" * 60)

    def loop(n):
        total = 0
        for i in range(n):
            total += i
        return total

    # 小循环可能不触发 Tier 2
    small_n = 5
    large_n = 10000

    print(f"  小循环 n={small_n}: 执行快，Tier 2 可能不介入")
    print(f"  大循环 n={large_n}: 触发 Tier 2 优化")

    # 大循环性能（预热后）
    loop(large_n)
    t = time.perf_counter()
    for _ in range(1000):
        loop(large_n)
    elapsed = time.perf_counter() - t
    print(f"  大循环 1000 次总耗时: {elapsed:.4f}s")

    # ── 4. 函数调用内联的潜在收益 ──────────────────────────
    print("\n" + "=" * 60)
    print("4. 调用内联的收益")
    print("=" * 60)

    def add(a, b):
        return a + b

    def with_call(n):
        total = 0
        for i in range(n):
            total = add(total, i)
        return total

    def inlined(n):
        total = 0
        for i in range(n):
            total = total + i
        return total

    n = 10000
    with_call(n)
    inlined(n)

    t = time.perf_counter()
    for _ in range(1000):
        with_call(n)
    t_call = time.perf_counter() - t

    t = time.perf_counter()
    for _ in range(1000):
        inlined(n)
    t_inline = time.perf_counter() - t

    print(f"  调用内联前: {t_call:.4f}s")
    print(f"  调用内联后: {t_inline:.4f}s")
    print("  Tier 2 可以自动做这种内联")
    print("  (但因无法强制触发 Tier 2，此处仅为概念演示)")


if __name__ == "__main__":
    main()
