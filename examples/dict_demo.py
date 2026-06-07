"""PyDictObject 探针 —— 观察 Python 字典的内部机制。

演示内容：
  - 字典的哈希表结构（dk_indices + dk_entries）
  - 哈希冲突解决
  - 扩容机制
  - 分离表 (split table) 优化
  - 插入顺序保持
  - 版本号变化
"""

import ctypes

# PyDictObject 字段偏移 (64-bit)
# PyObject_HEAD: 16B
# ma_used (Py_ssize_t): +16, 8B
# _ma_watcher_tag (uint64_t): +24, 8B
# ma_keys (PyDictKeysObject*): +32, 8B
# ma_values (PyDictValues*): +40, 8B

# PyDictKeysObject 字段偏移
# dk_refcnt (Py_ssize_t): 0, 8B
# dk_log2_size (uint8_t): +8, 1B
# dk_log2_index_bytes (uint8_t): +9, 1B
# dk_kind (uint8_t): +10, 1B
# dk_version (uint32_t): +12, 4B
# dk_usable (Py_ssize_t): +16, 8B
# dk_nentries (Py_ssize_t): +24, 8B


def read_dict_keys(d: dict) -> dict:
    """读取字典的 ma_keys 内部信息。"""
    addr = id(d)
    keys_ptr = ctypes.c_void_p.from_address(addr + 32).value

    if not keys_ptr:
        return {"error": "ma_keys is NULL"}

    dk_refcnt = ctypes.c_ssize_t.from_address(keys_ptr).value
    dk_log2_size = ctypes.c_uint8.from_address(keys_ptr + 8).value
    dk_kind = ctypes.c_uint8.from_address(keys_ptr + 10).value
    dk_version = ctypes.c_uint32.from_address(keys_ptr + 12).value
    dk_usable = ctypes.c_ssize_t.from_address(keys_ptr + 16).value
    dk_nentries = ctypes.c_ssize_t.from_address(keys_ptr + 24).value

    dk_size = 1 << dk_log2_size

    return {
        "keys_ptr": hex(keys_ptr),
        "size": dk_size,
        "log2_size": dk_log2_size,
        "refcnt": dk_refcnt,
        "usable": dk_usable,
        "nentries": dk_nentries,
        "version": dk_version,
        "kind": dk_kind,
    }


def read_dict_ma_values(d: dict):
    """读取 ma_values 指针，判断是 combined 还是 split table。"""
    addr = id(d)
    return ctypes.c_void_p.from_address(addr + 40).value


def main() -> None:
    print("=" * 60)
    print("PyDictObject 字典内部探针")
    print("=" * 60)

    # ── 1. 基础字典创建 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 字典创建与容量")
    print("=" * 60)

    d = {}
    info = read_dict_keys(d)
    print(f"  空字典: size={info['size']}, usable={info['usable']}")

    d["a"] = 1
    info = read_dict_keys(d)
    print(f"  1 个键: size={info['size']}, usable={info['usable']}, "
          f"nentries={info['nentries']}, version={info['version']}")

    # ── 2. 扩容观察 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 扩容观察")
    print("=" * 60)

    d2 = {}
    for i in range(12):
        d2[f"key{i}"] = i
        info = read_dict_keys(d2)
        if i < 3 or i == 5 or i == 11:
            print(f"  插入 key{i}: size={info['size']}, "
                  f"nentries={info['nentries']}, "
                  f"usable={info['usable']}")

    # ── 3. 分离表 vs 组合表 ────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 分离表 vs 组合表")
    print("=" * 60)

    class MyClass:
        def __init__(self):
            self.x = 1
            self.y = 2

    obj = MyClass()
    instance_dict = obj.__dict__

    # 实例属性字典通常使用 split table
    ma_values_ptr = read_dict_ma_values(instance_dict)
    if ma_values_ptr:
        print("  实例 __dict__: split table (ma_values != NULL)")
    else:
        print("  实例 __dict__: combined table (ma_values == NULL)")

    # 普通字典使用 combined table
    normal_dict = {"a": 1, "b": 2}
    ma_values_ptr = read_dict_ma_values(normal_dict)
    print(f"  普通字典: ma_values={hex(ma_values_ptr) if ma_values_ptr else 'NULL'} "
          f"(combined table)")

    # 比较两个同样属性的实例是否共享键表
    obj2 = MyClass()
    keys1_ptr = ctypes.c_void_p.from_address(id(obj.__dict__) + 32).value
    keys2_ptr = ctypes.c_void_p.from_address(id(obj2.__dict__) + 32).value
    print(f"  两个实例共享键表: {keys1_ptr == keys2_ptr}")

    # ── 4. 插入顺序 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("4. 插入顺序")
    print("=" * 60)

    d3 = {}
    d3["z"] = 1  # 先插入，但在哈希表末尾
    d3["a"] = 2
    d3["m"] = 3

    print(f"  dict = {d3}")
    print("  迭代顺序 = 插入顺序，因为 nentries 递增")

    # ── 5. 版本号变化 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. 版本号变化")
    print("=" * 60)

    d4 = {}
    versions = []
    for i in range(5):
        d4[f"k{i}"] = i
        info = read_dict_keys(d4)
        versions.append(info["version"])

    print(f"  修改前 version: {versions[0]}")
    d4["k0"] = 999
    info = read_dict_keys(d4)
    print(f"  修改后 version: {info['version']}")

    del d4["k0"]
    info = read_dict_keys(d4)
    print(f"  删除后 version: {info['version']}")

    # ── 6. 哈希冲突观察 ──────────────────────────────────
    print("\n" + "=" * 60)
    print("6. 哈希表索引")
    print("=" * 60)

    test_dict = {"hello": 1, "world": 2, "python": 3, "dict": 4, "hash": 5}
    info = read_dict_keys(test_dict)
    print(f"  5 个键的表: size={info['size']}, "
          f"nentries={info['nentries']}")

    # 查看每个键的哈希值和索引
    for key in test_dict:
        h = hash(key)
        idx = h & (info["size"] - 1)
        print(f"  hash('{key}') = {h:>20d}, index = {idx}")


if __name__ == "__main__":
    main()
