"""__slots__ 探针 — 观察内存和访问速度差异。"""

import sys
import time


class Normal:
    def __init__(self):
        self.x = 1
        self.y = 2


class WithSlots:
    __slots__ = ("x", "y")

    def __init__(self):
        self.x = 1
        self.y = 2


def main() -> None:
    print("=" * 60)
    print("__slots__ 探针")
    print("=" * 60)

    # ── 1. 内存对比 ────────────────────────────────────────
    print("\n1. 内存对比")
    n = Normal()
    s = WithSlots()
    print(f"  Normal 实例:   {sys.getsizeof(n)} 字节")
    print(f"  WithSlots 实例: {sys.getsizeof(s)} 字节")
    print(f"  节省: {sys.getsizeof(n) - sys.getsizeof(s)} 字节")

    # ── 2. __dict__ 存在性 ────────────────────────────────
    print("\n2. __dict__ 存在性")
    print(f"  Normal 有 __dict__:   {hasattr(n, '__dict__')}")
    print(f"  WithSlots 有 __dict__: {hasattr(s, '__dict__')}")

    # ── 3. 访问速度 ────────────────────────────────────────
    print("\n3. 访问速度对比")
    n = Normal()
    s = WithSlots()
    n.x = 10
    s.x = 10

    n_iter = 10_000_000

    t = time.perf_counter()
    for _ in range(n_iter):
        _ = n.x
    t_normal = time.perf_counter() - t

    t = time.perf_counter()
    for _ in range(n_iter):
        _ = s.x
    t_slots = time.perf_counter() - t

    print(f"  Normal 访问 {n_iter} 次:   {t_normal:.3f}s")
    print(f"  WithSlots 访问 {n_iter} 次: {t_slots:.3f}s")
    print(f"  加速: {t_normal / t_slots:.1f}x")

    # ── 4. 未定义 slot 的访问 ──────────────────────────────
    print("\n4. slot 限制验证")
    try:
        s.z = 999
    except AttributeError as e:
        print(f"  设置未定义 slot: AttributeError - {e}")


if __name__ == "__main__":
    main()
