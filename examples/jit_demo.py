"""JIT 编译器探针 — 观察从字节码到机器码的优化路径。

演示内容：
  - 执行路径的三层架构
  - 预热曲线
  - 内联函数调用的收益
  - 类型稳定性对 JIT 的重要性
"""

import time


def main() -> None:
    print("=" * 60)
    print("JIT 编译器探针")
    print("=" * 60)

    # ── 1. 三层执行架构 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 三层执行路径")
    print("=" * 60)

    print("""
    字节码 (bytecode)
         │
         ▼
    Tier 1 解释器 ── 逐条执行，自适应特化
         │                ~50M ops/s
         │ (循环触发优化)
         ▼
    Tier 2 微码执行器 ── 批量执行微码序列
         │                ~150M ops/s
         │ (升温触发 JIT)
         ▼
    JIT 原生机器码 ──── 直接执行机器码
                        ~500M ops/s
    """)

    # ── 2. 预热概念演示 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 预热曲线概念")
    print("=" * 60)

    def hot_loop(n):
        total = 0
        for i in range(n):
            total += i * i + i * i
        return total

    # 多次运行同一函数，观察时间变化
    n = 100000
    times = []
    for trial in range(5):
        start = time.perf_counter()
        hot_loop(n)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        label = "Tier 1" if trial == 0 else "Tier 2" if trial < 3 else "JIT"
        print(f"  第 {trial+1} 次 ({label}): {elapsed:.6f}s")

    print(f"  首次 vs 末次 加速: {times[0] / times[-1]:.1f}x")

    # ── 3. 可内联的小函数模式 ──────────────────────────────
    print("\n" + "=" * 60)
    print("3. JIT 受益模式 — 内联可优化")
    print("=" * 60)

    def add(a, b):
        return a + b

    def mul(a, b):
        return a * b

    # 模式 1：频繁的小函数调用
    def with_function_calls(n):
        total = 0
        for i in range(n):
            total = add(total, i)
        return total

    # 模式 2：直接内联运算
    def inlined(n):
        total = 0
        for i in range(n):
            total = total + i
        return total

    n = 50000

    # 预热
    with_function_calls(n)
    inlined(n)

    t = time.perf_counter()
    with_function_calls(n)
    t1 = time.perf_counter() - t

    t = time.perf_counter()
    inlined(n)
    t2 = time.perf_counter() - t

    print(f"  调用函数: {t1:.4f}s")
    print(f"  直接内联: {t2:.4f}s")
    print("  JIT 的 Copy-and-Patch 可以消除函数调用开销")
    print("  (JIT 内联的收益类似上面的差异)")

    # ── 4. 类型稳定性 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("4. 类型稳定性对 JIT 的影响")
    print("=" * 60)

    def type_stable(n):
        """始终用 int — 对 JIT 友好。"""
        total = 0
        for i in range(n):
            total += i
        return total

    def type_unstable(n):
        """混合类型 — JIT 难以优化。"""
        total = 0.0
        for i in range(n):
            if i % 2 == 0:
                total += i       # int
            else:
                total += float(i)  # float
        return total

    n = 50000
    type_stable(n)
    type_unstable(n)

    t = time.perf_counter()
    for _ in range(100):
        type_stable(n)
    t_stable = time.perf_counter() - t

    t = time.perf_counter()
    for _ in range(100):
        type_unstable(n)
    t_unstable = time.perf_counter() - t

    print(f"  类型稳定 (int):   {t_stable:.4f}s")
    print(f"  类型不稳定 (混搭): {t_unstable:.4f}s")
    print(f"  差异: {t_unstable / t_stable:.1f}x")
    print("  JIT 对类型稳定的代码优化效果最佳")


if __name__ == "__main__":
    main()
