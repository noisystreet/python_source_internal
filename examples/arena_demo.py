"""Arena 内存管理探针。

演示内容：
  - Arena/Pool/Block 大小关系
  - mmap 检测
  - 大量分配对 Arena 的影响
"""

import os
import sys


def main() -> None:
    print("=" * 60)
    print("Arena 内存管理探针")
    print("=" * 60)

    # ── 1. 尺寸常量 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. Arena/Pool/Block 尺寸")
    print("=" * 60)

    # 从 CPython 源码中的常量
    arena_bits = 20  # 1 MiB
    arena_size = 1 << arena_bits
    pool_bits = 14   # 16 KiB
    pool_size = 1 << pool_bits

    print(f"  Arena:     {arena_size:>10} 字节 ({arena_size // 1024} KiB)")
    print(f"  Pool:      {pool_size:>10} 字节 ({pool_size // 1024} KiB)")
    print("  对齐:      16 字节")
    print(f"  每 Arena Pool 数: {(1 << arena_bits) // (1 << pool_bits)}")

    # ── 2. 大小类与 Pool ──────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 大小类与 Pool 容量")
    print("=" * 60)

    header_size = 64  # pool_header 近似大小
    for block_size in [16, 32, 64, 128, 256, 512]:
        blocks_per_pool = (pool_size - header_size) // block_size
        print(f"  {block_size:>4}B blocks: {blocks_per_pool:>5} 个/pool")

    # ── 3. mmap 支持检测 ──────────────────────────────────
    print("\n" + "=" * 60)
    print("3. mmap 支持检测")
    print("=" * 60)

    have_mmap = hasattr(os, "mmap")
    print(f"  mmap 可用: {have_mmap}")

    # ── 4. 模拟 Arena 使用 ────────────────────────────────
    print("\n" + "=" * 60)
    print("4. arena 使用模拟")
    print("=" * 60)

    # 一个对象大约占 32 字节（object 本身）
    # 一个 Arena 可以放约 32K 个这样的对象
    obj_size = sys.getsizeof(object())
    objects_per_pool = (pool_size - header_size) // obj_size
    objects_per_arena = objects_per_pool * ((1 << arena_bits) // (1 << pool_bits))

    print(f"  object() 大小:         {obj_size} 字节")
    print(f"  每 Pool 可放:          {objects_per_pool} 个")
    print(f"  每 Arena (1 MiB) 可放: {objects_per_arena} 个")

    # 创建大量对象观察
    n = 50000
    print(f"\n  创建 {n} 个 object():")
    objs = [object() for _ in range(n)]
    print(f"  总内存 (近似): {sys.getsizeof(objs) + n * obj_size:,} 字节")
    print(f"  约 {n / objects_per_arena:.1f} 个 Arena")

    # ── 5. 释放观察 ───────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. 释放 — Arena 回到空闲池")
    print("=" * 60)

    del objs
    print("  对象已释放，Arena 等待重用")
    print("  （Pool 全部空闲后 Arena 才释放）")


if __name__ == "__main__":
    main()
