"""PyObject 内存布局探针

通过 ctypes 直接读取 CPython 对象在 C 层的内存布局，验证 PyObject 头部结构。

PyObject 头部布局 (64-bit, 标准构建):
  +0: ob_refcnt  (uint32_t)  — 引用计数
  +4: ob_flags   (uint16_t)  — 对象标志位
  +6: ob_overflow (uint16_t) — 溢出计数
  +8: ob_type    (void*/8B)  — 类型对象指针

PyVarObject 额外字段:
  +16: ob_size   (Py_ssize_t) — 元素个数
"""

import ctypes
import sys

# ctypes 类型别名
c_ssize_t = ctypes.c_ssize_t
c_uint32 = ctypes.c_uint32
c_uint16 = ctypes.c_uint16
c_void_p = ctypes.c_void_p

# 小整数缓存 (-5 ~ 257) 是小整数池的一部分
# 这些对象在一次进程生命周期中始终存在
SMALL_INT = 42
NORMAL_INT = 99999


def read_pyobject_header(addr: int) -> dict:
    """在给定内存地址处读取 PyObject 头部字段（64位系统假设）。

    注意：ctypes 读取时需注意字节顺序。本函数假设 little-endian。
    """
    base = addr
    refcnt = c_uint32.from_address(base).value
    ob_flags = c_uint16.from_address(base + 4).value
    ob_overflow = c_uint16.from_address(base + 6).value
    ob_type = c_void_p.from_address(base + 8).value

    return {
        "address": hex(addr),
        "refcount": refcnt,
        "flags": ob_flags,
        "overflow": ob_overflow,
        "type_ptr": hex(ob_type) if ob_type else None,
    }


def read_pyvarobject_size(addr: int) -> int:
    """读取 PyVarObject.ob_size（位于 PyObject 头部之后）。"""
    return c_ssize_t.from_address(addr + 16).value


def is_immortal(refcount: int) -> bool:
    """判断引用计数是否表示 immortal 对象（64位系统）。"""
    return (refcount & 0x80000000) != 0


def main() -> None:
    print("=" * 60)
    print("PyObject 头部内存布局探针 (64-bit 系统)")
    print("=" * 60)

    # ── 1. 整数对象 ──────────────────────────────────────────────
    x = NORMAL_INT
    hdr = read_pyobject_header(id(x))

    print("\n--- 整数对象 ---")
    print(f"值:      {NORMAL_INT}")
    print(f"地址:    {hdr['address']}")
    print(f"refcount: {hdr['refcount']} (0x{hdr['refcount']:08x})"
          f"{' [immortal]' if is_immortal(hdr['refcount']) else ''}")
    print(f"flags:   {hdr['flags']:#06x}")
    print(f"type:    {hdr['type_ptr']} → {type(x).__name__}")

    # ── 2. 小整数池（观察 immortal 效果） ──────────────────────
    a = SMALL_INT
    b = SMALL_INT
    hdr_a = read_pyobject_header(id(a))

    print("\n--- 小整数池 (interned) ---")
    print(f"值:        {SMALL_INT}")
    print(f"a 地址:    {id(a):#x}, b 地址: {id(b):#x}, 同一对象: {a is b}")
    print(f"refcount:  {hdr_a['refcount']} (0x{hdr_a['refcount']:08x})"
          f"{' [immortal]' if is_immortal(hdr_a['refcount']) else ''}")
    print("          小整数池中的对象通常是 immortal 的")

    # ── 3. 字符串对象 (PyVarObject) ────────────────────────────
    s = "Hello CPython"
    hdr_s = read_pyobject_header(id(s))
    strlen = read_pyvarobject_size(id(s))

    print("\n--- 字符串对象 (PyVarObject) ---")
    print(f"值:      '{s}'")
    print(f"地址:    {hdr_s['address']}")
    print(f"refcount: {hdr_s['refcount']} (0x{hdr_s['refcount']:08x})"
          f"{' [immortal]' if is_immortal(hdr_s['refcount']) else ''}")
    print(f"ob_size:  {strlen} (字符数)")
    print(f"type:    {hdr_s['type_ptr']} → {type(s).__name__}")

    # ── 4. 列表对象 (PyVarObject) ───────────────────────────────
    lst = [1, 2, 3]
    hdr_lst = read_pyobject_header(id(lst))
    list_len = read_pyvarobject_size(id(lst))

    print("\n--- 列表对象 (PyVarObject) ---")
    print(f"值:      {lst}")
    print(f"地址:    {hdr_lst['address']}")
    print(f"refcount: {hdr_lst['refcount']} (0x{hdr_lst['refcount']:08x})"
          f"{' [immortal]' if is_immortal(hdr_lst['refcount']) else ''}")
    print(f"ob_size:  {list_len} (元素个数)")
    print(f"type:    {hdr_lst['type_ptr']} → {type(lst).__name__}")

    # 增加引用并观察 refcount 变化
    lst_ref = lst  # noqa: F841
    hdr_lst2 = read_pyobject_header(id(lst))
    print(f"\n增加引用后 refcount: {hdr_lst2['refcount']}"
          f" {'(不变，immortal)' if is_immortal(hdr_lst2['refcount']) else ''}")

    # ── 5. Py_Is 等价性验证 ───────────────────────────────────────
    print("\n--- Py_Is 等价性验证 ---")
    print(f"sys.getrefcount(lst) = {sys.getrefcount(lst)}")
    print("(sys.getrefcount 多计 1，因参数传递产生了临时引用)")

    # ── 6. None 对象 (单例) ─────────────────────────────────────
    none_hdr = read_pyobject_header(id(None))
    print("\n--- None 对象 (单例) ---")
    print(f"地址:    {none_hdr['address']}")
    print(f"refcount: {none_hdr['refcount']} (0x{none_hdr['refcount']:08x})"
          f"{' [immortal]' if is_immortal(none_hdr['refcount']) else ''}")
    print(f"type:    {none_hdr['type_ptr']} → {type(None).__name__}")


if __name__ == "__main__":
    main()
