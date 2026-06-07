"""PyLongObject 探针 —— 观察 Python 整数的内部表示。

演示内容：
  - PyLongObject 结构：lv_tag + ob_digit[]
  - 小整数池 (small integer cache)
  - 大整数的变长 digit 数组
  - Compact vs non-compact 检测
  - 整数运算的 digit 级操作
"""

import ctypes

# PyLongObject 在 64 位系统上的布局
# PyObject_HEAD = 16 字节
# lv_tag (uintptr_t) = 8 字节，位于偏移 16
# ob_digit[0] (digit/uint32_t) 位于偏移 24

# CPython 3.12+ 的内部字段
PyLong_SHIFT = 30  # 64 位系统
PyLong_MASK = (1 << PyLong_SHIFT) - 1  # 0x3FFFFFFF

# 小整数范围
NSMALLNEGINTS = 5
NSMALLPOSINTS = 257

# lv_tag 位定义
_SIGN_MASK = 3
_NON_SIZE_BITS = 3


def read_tag(py_long_obj) -> int:
    """读取 lv_tag 字段（偏移 16，8 字节）。"""
    buf = ctypes.string_at(id(py_long_obj) + 16, 8)
    tag = int.from_bytes(buf, 'little')
    return tag


def read_digit(py_long_obj, index: int) -> int:
    """读取 ob_digit[index]（从偏移 24 开始，每个 4 字节）。"""
    buf = ctypes.string_at(id(py_long_obj) + 24 + index * 4, 4)
    return int.from_bytes(buf, 'little')


def analyze_int(val: int) -> dict:
    """分析一个整数的内部结构。"""
    obj = val
    addr = id(obj)
    tag = read_tag(obj)

    ndigits = tag >> _NON_SIZE_BITS
    sign_code = tag & _SIGN_MASK
    is_small = bool(tag & (1 << 2))

    if ndigits == 0:
        # compact: 值编码在 tag 中
        sign_map = {0: 1, 1: 0, 2: -1}
        sign = sign_map.get(sign_code, 0)
        actual_ndigits = 1
    else:
        sign_map = {0: 1, 1: 0, 2: -1}
        sign = sign_map.get(sign_code, 0)
        actual_ndigits = ndigits

    digits = []
    for i in range(actual_ndigits):
        digits.append(read_digit(obj, i))

    return {
        "address": hex(addr),
        "tag": tag,
        "ndigits": actual_ndigits,
        "sign": sign,
        "digits": digits,
        "compact": ndigits == 0,
        "is_small_int": is_small,
    }


def main() -> None:
    print("=" * 60)
    print("PyLongObject 整数内部探针")
    print("=" * 60)

    # ── 1. 小整数池 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 小整数池 (Small Integer Cache)")
    print("=" * 60)

    for val in [0, 1, 42, 256, 257, 258, 99999]:
        a = val
        b = val
        same = a is b
        info = analyze_int(a)
        compact_label = "compact" if info["compact"] else f"{info['ndigits']} digits"
        print(f"  {val:>6}: id(a)={id(a):#x}, id(b)={id(b):#x}, "
              f"同一对象={same}, {compact_label}")

    # ── 2. 大整数的 digit 数组 ─────────────────────────────
    print("\n" + "=" * 60)
    print("2. 大整数的 digit 数组")
    print("=" * 60)

    big = 2 ** 1000
    info = analyze_int(big)
    print("\n  2**1000 的内部结构:")
    print(f"  地址:      {info['address']}")
    print(f"  tag:       {info['tag']} (0x{info['tag']:x})")
    print(f"  ndigits:   {info['ndigits']}")
    print(f"  符号:      {'负' if info['sign'] < 0 else '正'}")
    print(f"  前 5 个 digit: {info['digits'][:5]}")
    print(f"  后 5 个 digit: {info['digits'][-5:]}")
    print(f"  总位数:    {info['ndigits'] * 30} (实际约 1000 bit)")

    # 恢复值
    recovered = 0
    for i, d in enumerate(info['digits']):
        recovered += d << (PyLong_SHIFT * i)
    if info['sign'] < 0:
        recovered = -recovered
    print(f"  恢复验证:  2**1000 == {recovered == 2**1000}")

    # ── 3. 超大整数 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 超大整数")
    print("=" * 60)

    huge = 2 ** 100000
    info_huge = analyze_int(huge)
    print(f"\n  2**100000 的 digit 数: {info_huge['ndigits']}")
    print(f"  估算内存占用: {16 + 8 + info_huge['ndigits'] * 4} 字节")

    # ── 4. 负数 ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("4. 负数")
    print("=" * 60)

    for val in [-1, -42, -2 ** 100]:
        info = analyze_int(val)
        print(f"  {val:>10}: sign={info['sign']}, digits={info['digits'][:3]}...")

    # ── 5. 零 ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. 零的特殊表示")
    print("=" * 60)

    info = analyze_int(0)
    print(f"  0: tag={info['tag']}, sign={info['sign']}")
    print("     (零的 sign_code 是 1，表示 'zero')")

    # ── 6. 整数运算对 digit 的影响 ─────────────────────────
    print("\n" + "=" * 60)
    print("6. 运算对 digit 的影响")
    print("=" * 60)

    a = 2 ** 60  # 2 个 digit
    b = 2 ** 60
    c = a + b    # 需要进位，可能变成 3 个 digit

    info_a = analyze_int(a)
    info_c = analyze_int(c)
    print(f"  2**60:       {info_a['ndigits']} digit(s), digits={info_a['digits']}")
    print(f"  2**60+2**60: {info_c['ndigits']} digit(s), digits={info_c['digits']}")
    print("  (加法导致了进位)")

    # ── 7. int 的 tp_as_number 函数表 ─────────────────────
    print("\n" + "=" * 60)
    print("7. int 类型支持的操作")
    print("=" * 60)

    ops = [
        ("+", 3 + 5),
        ("-", 10 - 3),
        ("*", 7 * 8),
        ("//", 17 // 3),
        ("%", 17 % 3),
        ("**", 2 ** 10),
        ("&", 0b1010 & 0b1100),
        ("|", 0b1010 | 0b1100),
        ("^", 0b1010 ^ 0b1100),
        ("<<", 1 << 10),
        (">>", 1024 >> 3),
    ]
    for op_name, result in ops:
        print(f"  {op_name:>3}: {result}")


if __name__ == "__main__":
    main()
