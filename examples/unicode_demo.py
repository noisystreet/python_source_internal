"""PyUnicodeObject 探针 —— 观察 Python 字符串的内部表示。

演示内容：
  - PEP 393 紧凑表示：1/2/4 字节每字符
  - ASCII vs 非 ASCII 字符串的结构差异
  - Interning（字符串驻留）
  - 哈希缓存
  - 拼接性能对比
"""

import ctypes
import time

# PyASCIIObject 字段偏移 (64-bit)
# PyObject_HEAD: 16 字节
# length (Py_ssize_t): 偏移 16，8 字节
# hash (Py_hash_t): 偏移 24，8 字节
# state: 偏移 32，2 字节
# (data 紧接在结构体之后)


def read_unicode_state(s: str) -> dict:
    """读取 PyASCIIObject 的 state 和 length 字段。"""
    addr = id(s)
    length = ctypes.c_ssize_t.from_address(addr + 16).value
    hash_val = ctypes.c_ssize_t.from_address(addr + 24).value

    # state 字段（2 字节，在偏移 32 处）
    state_bits = ctypes.c_uint16.from_address(addr + 32).value

    interned = state_bits & 0b11
    kind = (state_bits >> 2) & 0b111
    compact = (state_bits >> 5) & 1
    ascii = (state_bits >> 6) & 1
    ready = (state_bits >> 7) & 1

    return {
        "length": length,
        "hash": hash_val,
        "interned": interned,
        "kind": kind,
        "compact": bool(compact),
        "ascii": bool(ascii),
        "ready": bool(ready),
    }


def kind_to_name(kind: int) -> str:
    names = {1: "1-byte (Latin-1)", 2: "2-byte (UCS-2)", 4: "4-byte (UCS-4)"}
    return names.get(kind, "unknown")


def main() -> None:
    print("=" * 60)
    print("PyUnicodeObject 字符串内部探针")
    print("=" * 60)

    # ── 1. 不同字符宽度的字符串 ────────────────────────────
    print("\n" + "=" * 60)
    print("1. 字符串的三种内部表示")
    print("=" * 60)

    strings = [
        ("hello", "纯 ASCII"),
        ("café", "Latin-1 扩展"),
        ("你好", "中文 (BMP)"),
        ("😊", "Emoji (补充平面)"),
    ]

    for s, desc in strings:
        info = read_unicode_state(s)
        chars_per = {1: 1, 2: 2, 4: 4}.get(info["kind"], "?")
        print(f"  '{s}' ({desc}):")
        print(f"    length={info['length']}, kind={info['kind']} "
              f"({chars_per} 字节/字符), ascii={info['ascii']}, "
              f"compact={info['compact']}")
        print(f"    hash={'未计算' if info['hash'] == -1 else hex(info['hash'])}")

    # ── 2. Interning ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. Interning (字符串驻留)")
    print("=" * 60)

    # 标识符风格字符串通常被 intern
    a = "hello"
    b = "hello"
    interned = read_unicode_state(a)['interned']
    print(f"  'hello' is 'hello': {a is b} (interned={interned})")

    # 带空格的通常不被 intern（除非很短）
    c = "a b"
    d = "a b"
    print(f"  'a b' is 'a b': {c is d}")

    # 长字符串通常不被 intern
    e = "hello world " * 10
    f = "hello world " * 10
    print(f"  长字符串 is 比较: {e is f}")

    # 代码对象中的字符串 — co_names 中的 'x' 通常被 intern
    info = read_unicode_state("x")
    print(f"  'x' 的 interned 状态: {info['interned']} "
          f"(0=未intern, 1=已intern, 2=intern+immortal)")

    # ── 3. 哈希缓存 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 哈希缓存")
    print("=" * 60)

    s = "hello_python_world"
    info_before = read_unicode_state(s)
    cached = '未设置' if info_before['hash'] == -1 else '已设置'
    print(f"  调用 hash() 前: hash 缓存={cached}")

    h = hash(s)
    print(f"  hash(s) = {h}")

    info_after = read_unicode_state(s)
    print(f"  调用后: hash 缓存={'未设置' if info_after['hash'] == -1 else '已设置'}")
    print(f"  缓存值: {info_after['hash']}")

    # 再次调用，直接返回缓存
    h2 = hash(s)
    print(f"  第二次 hash(s): {h2}（验证为缓存，O(1)）")

    # ── 4. 不同内容的字符串内存占用 ─────────────────────────
    print("\n" + "=" * 60)
    print("4. 字符串内存占用对比")
    print("=" * 60)

    s_ascii = "a" * 1000
    s_ucs2 = "好" * 1000
    s_ucs4 = "😊" * 1000

    info_ascii = read_unicode_state(s_ascii)
    info_ucs2 = read_unicode_state(s_ucs2)
    info_ucs4 = read_unicode_state(s_ucs4)

    bytes_per = {1: 1, 2: 2, 4: 4}
    for name, s, info in [("ASCII", s_ascii, info_ascii),
                           ("UCS-2", s_ucs2, info_ucs2),
                           ("UCS-4", s_ucs4, info_ucs4)]:
        bp = bytes_per.get(info["kind"], 0)
        data_size = info["length"] * bp
        header_size = 48 if info["compact"] else 56  # 估算
        print(f"  {name:>6}: {info['length']:>5} 字符 × {bp} 字节 = "
              f"{data_size:>5}B 数据 + ~{header_size}B 头部")

    # ── 5. join vs += 性能对比 ─────────────────────────────
    print("\n" + "=" * 60)
    print("5. 拼接性能对比")
    print("=" * 60)

    n = 10000
    parts = [str(i) for i in range(n)]

    # join 方法
    start = time.perf_counter()
    result1 = "".join(parts)
    t_join = time.perf_counter() - start

    # += 循环
    start = time.perf_counter()
    result2 = ""
    for p in parts:
        result2 += p
    t_plus = time.perf_counter() - start

    print(f"  n={n}")
    print(f"  ''.join(): {t_join:.4f}s")
    print(f"  += 循环:   {t_plus:.4f}s")
    print(f"  加速比:    {t_plus / t_join:.1f}x")
    print(f"  结果一致:  {result1 == result2}")


if __name__ == "__main__":
    main()
