"""PyTypeObject 探针 —— 观察类型对象的内部结构和字段。

演示内容：
  - 内置类型（int, str, list）的 ob_type 都指向 type
  - type 本身的 ob_type 指向自己
  - 查看 tp_name / tp_flags / tp_basicsize 等字段
  - MRO 验证
"""

import ctypes


# ctypes helper: read a C pointer from a given address
def read_ptr(addr: int) -> int:
    return ctypes.c_void_p.from_address(addr).value


def read_cstr(addr: int) -> str:
    """Read a null-terminated C string from memory."""
    if not addr:
        return "<NULL>"
    buf = []
    i = 0
    while True:
        b = ctypes.c_uint8.from_address(addr + i).value
        if b == 0:
            break
        buf.append(chr(b))
        i += 1
    return "".join(buf)


def read_ulong(addr: int) -> int:
    return ctypes.c_ulong.from_address(addr).value


def read_ssize(addr: int) -> int:
    return ctypes.c_ssize_t.from_address(addr).value


# Offset constants for PyTypeObject fields (64-bit, standard build)
# PyObject_VAR_HEAD = PyObject (16B) + ob_size (8B) = 24B
OFF_TP_NAME = 24           # after PyObject_VAR_HEAD
OFF_TP_BASICSIZE = 24 + 8  # after tp_name
OFF_TP_FLAGS = (
    24 + 8 + 8 +            # tp_name + tp_basicsize + tp_itemsize
    8 + 8 + 8 +              # tp_dealloc + tp_vectorcall_offset + tp_getattr
    8 + 8 + 8 +              # tp_setattr + tp_as_async + tp_repr
    8 + 8 + 8 +              # tp_as_number + tp_as_sequence + tp_as_mapping
    8 + 8 + 8 +              # tp_hash + tp_call + tp_str
    8 + 8 +                  # tp_getattro + tp_setattro
    8 +                      # tp_as_buffer
    0                        # right before tp_flags
)


def inspect_type(tp: type) -> dict:
    """Read metadata of a type object using ctypes."""
    addr = id(tp)
    # tp_name is the first field after PyObject_VAR_HEAD (24 bytes)
    tp_name_ptr = read_ptr(addr + 24)
    tp_name = read_cstr(tp_name_ptr)

    # tp_basicsize: after tp_name ptr (8 bytes)
    tp_basicsize = read_ssize(addr + 24 + 8)

    return {
        "address": hex(addr),
        "tp_name": tp_name,
        "tp_basicsize": tp_basicsize,
        "ob_type": type(tp),
    }


def main():
    print("=" * 60)
    print("PyTypeObject 探针")
    print("=" * 60)

    # 1. Verify that all types have ob_type pointing to type
    print("\n--- 所有类型的 ob_type ---")
    for name, tp in [("int", int), ("str", str), ("list", list),
                      ("dict", dict), ("tuple", tuple),
                      ("float", float), ("bool", bool)]:
        addr = id(tp)
        ob_type_ptr = read_ptr(addr + 8)  # ob_type at offset 8
        # resolve type name from the type object
        type_tp_name_ptr = read_ptr(ob_type_ptr + 24)
        type_name = read_cstr(type_tp_name_ptr) if type_tp_name_ptr else "?"
        print(f"  {name:>6}: ob_type -> {type_name} (0x{ob_type_ptr:x})")

    # 2. type itself
    print("\n--- type 本身 ---")
    type_addr = id(type)
    type_ob_type = read_ptr(type_addr + 8)
    type_tp_name_ptr = read_ptr(type_addr + 24)
    print(f"  type 地址:    0x{type_addr:x}")
    print(f"  type.ob_type: 0x{type_ob_type:x}")
    print(f"  type.tp_name: {read_cstr(type_tp_name_ptr)}")
    print(f"  是自身: {type_ob_type == type_addr}")

    # 3. tp_name field inspection
    print("\n--- tp_name 字段 ---")
    for name, tp in [("int", int), ("str", str), ("list", list),
                      ("type", type), ("object", object)]:
        info = inspect_type(tp)
        print(f"  {name:>6}: tp_name = {info['tp_name']}, "
              f"basicsize = {info['tp_basicsize']}")

    # 4. tp_flags
    print("\n--- tp_flags ---")
    for name, tp in [("int", int), ("str", str), ("list", list),
                      ("object", object)]:
        flags = tp.__flags__
        print(f"  {name:>6}: tp_flags = {flags} "
              f"(0b{flags:032b})")
        # check specific flags
        if flags & (1 << 3):
            print("         -> Py_TPFLAGS_HAVE_GC = True")
        if flags & (1 << 0):
            print("         -> Py_TPFLAGS_HEAPTYPE = True (heap type)")

    # 5. User-defined classes
    print("\n--- 用户定义类 ---")

    class MyClass:
        pass

    class Base:
        pass

    class Derived(Base):
        pass

    for name, cls in [("MyClass", MyClass), ("Base", Base),
                       ("Derived", Derived)]:
        info = inspect_type(cls)
        print(f"  {name:>8}: tp_name = {info['tp_name']}")
        print(f"             ob_type = {info['ob_type']}")
        print(f"             flags   = {cls.__flags__} "
              f"(heap: {bool(cls.__flags__ & (1 << 0))})")

    # 6. MRO verification
    print("\n--- MRO (方法解析顺序) ---")

    class A:
        pass

    class B(A):
        pass

    class C(A):
        pass

    class D(B, C):
        pass

    for i, cls in enumerate(D.__mro__):
        print(f"  D.__mro__[{i}] = {cls}")
    print(f"  MRO 长度: {len(D.__mro__)}")


if __name__ == "__main__":
    main()
