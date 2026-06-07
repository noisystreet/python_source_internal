"""obmalloc 探针 — 观察 Python 的小块内存分配器。

演示内容：
  - 大小类映射
  - pool 容量计算
  - 分配性能对比
  - 对象大小分布
"""

import ctypes
import sys
import time


def size_class(nbytes: int) -> tuple:
    """计算给定字节数对应的大小类和实际分配大小。"""
    alignment = 16  # 64 位系统
    if nbytes <= 512:
        # 向上取整到 16 的倍数
        actual = ((nbytes + alignment - 1) // alignment) * alignment
        class_idx = actual // alignment - 1
        return class_idx, actual
    else:
        return None, nbytes  # 走系统 malloc


def pool_capacity(class_idx: int) -> int:
    """计算给定大小类下，一个 pool 可以容纳多少 block。"""
    block_size = (class_idx + 1) * 16
    pool_size = 16 * 1024  # 16 KiB (large pool)
    header_size = 64  # pool_header 估算
    usable = pool_size - header_size
    return usable // block_size


def main() -> None:
    print("=" * 60)
    print("obmalloc 小块内存分配器探针")
    print("=" * 60)

    # ── 1. 大小类映射 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 大小类映射 (64-bit, 16 字节对齐)")
    print("=" * 60)

    test_sizes = [1, 10, 16, 17, 30, 33, 64, 100, 256, 500, 512, 600, 1024]
    for size in test_sizes:
        cls_idx, actual = size_class(size)
        if cls_idx is not None:
            print(f"  malloc({size:>4}) → 分配 {actual:>3} 字节 (class {cls_idx:>2})")
        else:
            print(f"  malloc({size:>4}) → 走系统 malloc (≥{512})")

    # ── 2. Pool 容量 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. Pool 容量")
    print("=" * 60)

    print("  Pool 大小: 16 KiB (16384 字节)")
    print("  头部开销: ~64 字节")
    for cls_idx in [0, 1, 2, 5, 10, 20, 31]:
        block_size = (cls_idx + 1) * 16
        cap = pool_capacity(cls_idx)
        print(f"  class {cls_idx:>2} ({block_size:>3}B): ~{cap} block/pool")

    # ── 3. 性能对比 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 分配性能对比 (obmalloc vs 系统 malloc)")
    print("=" * 60)

    n = 1000000

    # obmalloc 路径（小对象）
    start = time.perf_counter()
    objs = []
    for _ in range(n):
        objs.append(object())
    t_obmalloc = time.perf_counter() - start
    del objs[:]

    # 系统 malloc 路径（大对象走系统 malloc 的模拟）
    # 实际用 ctypes 直接调系统 malloc 做对比
    start = time.perf_counter()
    ptrs = []
    for _ in range(n // 10):  # 少一些，大对象慢
        ptrs.append(ctypes.create_string_buffer(1024))
    t_sys = time.perf_counter() - start
    del ptrs[:]

    print(f"  object() × {n} (obmalloc): {t_obmalloc:.3f}s, "
          f"{t_obmalloc / n * 1e9:.0f}ns/次")
    print(f"  1024B buffer × {n // 10} (系统 malloc): {t_sys:.3f}s")

    # ── 4. Python 对象大小分布 ────────────────────────────
    print("\n" + "=" * 60)
    print("4. Python 对象大小分布")
    print("=" * 60)

    objects = [
        ("object()", object()),
        ("None type", type(None)),
        ("42 (int)", 42),
        ("2**1000 (int)", 2 ** 1000),
        ("True", True),
        ("() (tuple)", ()),
        ("(1,2,3) (tuple)", (1, 2, 3)),
        ("[] (list)", []),
        ("dict", {}),
        ("set", set()),
        ("'hello'", "hello"),
    ]

    for name, obj in objects:
        size = sys.getsizeof(obj)
        cls_idx, actual = size_class(size)
        if cls_idx is not None:
            print(f"  {name:>20}: {size:>4}B → class {cls_idx} "
                  f"(pool 可存 {pool_capacity(cls_idx)} 个)")
        else:
            print(f"  {name:>20}: {size:>4}B → 走系统 malloc")

    # ── 5. 阈值边界 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. 阈值边界 (512 字节)")
    print("=" * 60)

    # 创建一个大的自定义对象来演示
    class Small:
        __slots__ = ("x", "y", "z")

    class Large:
        __slots__ = tuple(f"attr_{i}" for i in range(100))

    print(f"  Small (3 slots):  {sys.getsizeof(Small)} 字节 → "
          f"{'obmalloc' if sys.getsizeof(Small) <= 512 else '系统 malloc'}")
    print(f"  Large (100 slots): {sys.getsizeof(Large)} 字节 → "
          f"{'obmalloc' if sys.getsizeof(Large) <= 512 else '系统 malloc'}")


if __name__ == "__main__":
    main()
