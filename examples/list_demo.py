"""PyListObject 探针 —— 观察 Python 列表的内部机制。

演示内容：
  - PyListObject 结构（ob_item, allocated, ob_size）
  - append 扩容策略
  - insert/pop 的复杂度差异
  - Timsort 排序
"""

import ctypes
import time

# PyListObject 字段偏移 (64-bit)
# PyObject_VAR_HEAD: PyObject_HEAD(16B) + ob_size(8B) = 24B
# ob_item (PyObject**): +24, 8B
# allocated (Py_ssize_t): +32, 8B


def read_list_info(lst: list) -> dict:
    """读取 PyListObject 的内部字段。"""
    addr = id(lst)
    ob_size = ctypes.c_ssize_t.from_address(addr + 16).value  # PyVarObject.ob_size
    ob_item_ptr = ctypes.c_void_p.from_address(addr + 24).value
    allocated = ctypes.c_ssize_t.from_address(addr + 32).value

    # 读取前几个元素指针
    elements = []
    if ob_item_ptr and ob_size > 0:
        for i in range(min(ob_size, 5)):
            ptr = ctypes.c_void_p.from_address(ob_item_ptr + i * 8).value
            elements.append(hex(ptr) if ptr else "NULL")

    return {
        "len": ob_size,
        "allocated": allocated,
        "ob_item": hex(ob_item_ptr) if ob_item_ptr else "NULL",
        "elements": elements,
    }


def main() -> None:
    print("=" * 60)
    print("PyListObject 列表内部探针")
    print("=" * 60)

    # ── 1. 空列表 ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 空列表")
    print("=" * 60)

    lst = []
    info = read_list_info(lst)
    print(f"  len={info['len']}, allocated={info['allocated']}, "
          f"ob_item={info['ob_item']}")

    # ── 2. append 对容量的影响 ─────────────────────────────
    print("\n" + "=" * 60)
    print("2. append 对容量的影响")
    print("=" * 60)

    lst2 = []
    for i in range(12):
        lst2.append(i)
        size = len(lst2)
        # 只在容量变化时打印
        info = read_list_info(lst2)
        if size == 1 or size == 5 or size == 9 or size == 11 \
           or i == 11:
            print(f"  append {size:>2} 个: len={info['len']}, "
                  f"allocated={info['allocated']}")

    # ── 3. 索引访问 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 索引访问")
    print("=" * 60)

    lst3 = [10, 20, 30, 40, 50]
    info = read_list_info(lst3)
    print(f"  列表: {lst3}")
    print(f"  ob_item ptr: {info['ob_item']}")
    print(f"  元素指针: {info['elements']}")

    # 通过 ob_item 直接读取元素
    ob_item = int(info['ob_item'], 16)
    for i in range(len(lst3)):
        ptr = ctypes.c_void_p.from_address(ob_item + i * 8).value
        # 读取元素的值（需要知道类型，这里只打印地址）
        print(f"  ob_item[{i}] = {hex(ptr)}")

    # ── 4. pop 对容量的影响 ────────────────────────────────
    print("\n" + "=" * 60)
    print("4. pop 对容量的影响")
    print("=" * 60)

    lst4 = list(range(20))
    info_before = read_list_info(lst4)
    print(f"  前: len={info_before['len']}, allocated={info_before['allocated']}")

    # pop 到空
    while lst4:
        lst4.pop()
    info_after = read_list_info(lst4)
    print(f"  后: len={info_after['len']}, allocated={info_after['allocated']}")
    print("  (list 不自动缩减容量，即使 pop 到空)")

    # ── 5. insert vs append 性能 ──────────────────────────
    print("\n" + "=" * 60)
    print("5. insert(0) vs append 性能")
    print("=" * 60)

    n = 10000

    # append
    lst5 = []
    start = time.perf_counter()
    for i in range(n):
        lst5.append(i)
    t_append = time.perf_counter() - start

    # insert(0)
    lst6 = []
    start = time.perf_counter()
    for i in range(n):
        lst6.insert(0, i)
    t_insert = time.perf_counter() - start

    print(f"  append × {n}:  {t_append:.4f}s")
    print(f"  insert(0) × {n}: {t_insert:.4f}s")
    print(f"  差异: {t_insert / t_append:.1f}x")
    print("  (insert(0) 每次都需要 memmove 所有元素)")

    # ── 6. sort ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("6. sort 性能")
    print("=" * 60)

    import random
    lst7 = list(range(10000))
    random.shuffle(lst7)
    start = time.perf_counter()
    lst7.sort()
    t_sort = time.perf_counter() - start
    print(f"  对 10000 个元素排序: {t_sort:.4f}s (Timsort)")

    # ── 7. 切片 ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("7. 切片（浅拷贝）")
    print("=" * 60)

    lst8 = [1, 2, 3, 4, 5]
    sliced = lst8[:3]
    info_orig = read_list_info(lst8)
    info_sliced = read_list_info(sliced)
    print(f"  原列表:  len={info_orig['len']}, ob_item={info_orig['ob_item']}")
    print(f"  切片[:3]: len={info_sliced['len']}, "
          f"ob_item={info_sliced['ob_item']}")
    print("  不同内存 => 切片是新的 PyListObject")


if __name__ == "__main__":
    main()
