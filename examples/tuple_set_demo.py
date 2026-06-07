"""PyTupleObject / PySetObject 探针。

演示内容：
  - tuple: 定长数组、哈希缓存、空元组单例
  - set: 哈希表、smalltable 优化、集合运算
"""

import ctypes

# ─── tuple 部分 ──────────────────────────────────────────────

# PyTupleObject 字段偏移 (64-bit)
# PyObject_VAR_HEAD: 24B
# ob_hash (Py_hash_t): +24, 8B
# ob_item[0]: +32


def read_tuple_info(t: tuple) -> dict:
    addr = id(t)
    length = ctypes.c_ssize_t.from_address(addr + 16).value  # ob_size
    ob_hash = ctypes.c_ssize_t.from_address(addr + 24).value

    # 读取元素指针
    elements = []
    for i in range(min(length, 5)):
        ptr = ctypes.c_void_p.from_address(addr + 32 + i * 8).value
        elements.append(hex(ptr) if ptr else "NULL")

    return {"len": length, "hash": ob_hash, "elements": elements}


# ─── set 部分 ────────────────────────────────────────────────


def read_set_info(s: set) -> dict:
    """读取 PySetObject 的关键字段。"""
    addr = id(s)
    used = ctypes.c_ssize_t.from_address(addr + 16).value
    # hash 在偏移 24
    fill = ctypes.c_ssize_t.from_address(addr + 32).value
    mask = ctypes.c_ssize_t.from_address(addr + 40).value
    table_ptr = ctypes.c_void_p.from_address(addr + 48).value
    smalltable_addr = addr + 56

    # 判断使用 smalltable 还是堆表
    using_small = (table_ptr == smalltable_addr)

    return {
        "used": used,
        "fill": fill,
        "mask": mask,
        "table": hex(table_ptr),
        "using_smalltable": using_small,
    }


def main():
    print("=" * 60)
    print("tuple / set 探针")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("tuple 部分")
    print("=" * 60)

    # ── 1. 空元组单例 ──────────────────────────────────────
    print("\n--- 空元组单例 ---")
    t1 = ()
    t2 = ()
    print(f"  () is (): {t1 is t2}")

    # ── 2. 哈希值缓存 ──────────────────────────────────────
    print("\n--- 哈希值缓存 ---")
    t = (1, 2, 3, "hello")
    info_before = read_tuple_info(t)
    print(f"  计算前: hash = {info_before['hash']}")

    _ = hash(t)  # 触发计算
    info_after = read_tuple_info(t)
    print(f"  计算后: hash = {info_after['hash']} (已缓存)")

    # 再次计算直接返回缓存
    import time
    start = time.perf_counter_ns()
    hash(t)
    t_cached = time.perf_counter_ns() - start

    # 创建一个新的大 tuple 需要计算
    t_big = tuple(range(1000))
    start = time.perf_counter_ns()
    hash(t_big)
    t_first = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    hash(t_big)
    t_cached_big = time.perf_counter_ns() - start

    print(f"  小 tuple 缓存命中: {t_cached}ns")
    print(f"  大 tuple 首次:     {t_first}ns")
    print(f"  大 tuple 缓存命中: {t_cached_big}ns")

    # ── 3. tuple 元素 ──────────────────────────────────────
    print("\n--- tuple 元素读取 ---")
    t3 = (10, 20, 30, 40, 50)
    info = read_tuple_info(t3)
    print(f"  tuple len: {info['len']}")
    for i, elem_addr in enumerate(info['elements']):
        print(f"  ob_item[{i}] = {elem_addr}")

    # ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("set 部分")
    print("=" * 60)

    # ── 4. 小集合 vs 大集合 ────────────────────────────────
    print("\n--- smalltable vs 哈希表 ---")
    small = {1, 2, 3}
    large = set(range(100))

    info_small = read_set_info(small)
    info_large = read_set_info(large)
    print(f"  小集合 (3 个): used={info_small['used']}, "
          f"smalltable={info_small['using_smalltable']}")
    print(f"  大集合 (100 个): used={info_large['used']}, "
          f"smalltable={info_large['using_smalltable']}")

    # ── 5. 集合运算 ────────────────────────────────────────
    print("\n--- 集合运算 ---")
    a = {1, 2, 3, 4, 5}
    b = {4, 5, 6, 7, 8}
    print(f"  a = {a}")
    print(f"  b = {b}")
    print(f"  a & b = {a & b}")
    print(f"  a | b = {a | b}")
    print(f"  a - b = {a - b}")
    print(f"  a ^ b = {a ^ b}")

    # ── 6. frozenset 哈希 ──────────────────────────────────
    print("\n--- frozenset 哈希 ---")
    fs = frozenset([3, 1, 4, 1, 5, 9])
    print(f"  frozenset = {fs}")
    print(f"  hash(fs) = {hash(fs)}")

    # ── 7. set 的负载因子 ──────────────────────────────────
    print("\n--- set 扩容 ---")
    s = set()
    for i in range(15):
        s.add(i)
        info = read_set_info(s)
        if i in [0, 5, 10, 14]:
            print(f"  添加 {i+1:>2} 个元素: used={info['used']}, "
                  f"mask=0x{info['mask']:x}, "
                  f"smalltable={info['using_smalltable']}")


if __name__ == "__main__":
    main()
