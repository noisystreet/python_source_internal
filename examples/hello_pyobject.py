"""Hello PyObject — 初探 CPython 对象模型。

通过 ctypes 查看 Python 对象的底层结构（refcount、type 指针等），
验证 CPython 对象模型的 C 层布局。
"""

import ctypes
import sys


def inspect_object(obj) -> dict:
    """检查任意 Python 对象的底层内存布局。

    每个 PyObject 头部包含：
      - ob_refcnt (py_ssize_t): 引用计数
      - ob_type    (PyTypeObject*): 类型对象指针
    """
    # py_ssize_t 在 64 位系统上是 8 字节
    refcnt = ctypes.c_ssize_t.from_address(id(obj))
    # type 指针在 refcnt 之后的 8 字节
    type_ptr = ctypes.c_void_p.from_address(id(obj) + 8)

    return {
        "id": hex(id(obj)),
        "refcount": refcnt.value,
        "type_ptr": hex(type_ptr.value),
        "type_name": type(obj).__name__,
    }


def main() -> None:
    print("=== PyObject 基础结构探针 ===\n")

    # 观察简单对象的引用计数
    x = 42
    info = inspect_object(x)
    print("整数 42:")
    print(f"  地址:      {info['id']}")
    print(f"  引用计数:  {info['refcount']}")
    print(f"  类型指针:  {info['type_ptr']}")
    print(f"  类型名:    {info['type_name']}")

    # 增加引用后观察 refcount 变化
    y = x  # noqa: F841
    info2 = inspect_object(x)
    print(f"\n执行 y = x 后，引用计数: {info2['refcount']}"
          f" (预期: {info['refcount'] + 1})")

    # 字符串对象同样适用
    s = "hello"
    info3 = inspect_object(s)
    print("\n字符串 'hello':")
    print(f"  地址:      {info3['id']}")
    print(f"  引用计数:  {info3['refcount']}")
    print(f"  类型名:    {info3['type_name']}")

    # sys.getrefcount 会多计 1（传入参数时的临时引用）
    print(f"\nsys.getrefcount(s): {sys.getrefcount(s)}")
    print("(比手动查看多 1，因为参数传递增加了临时引用)")


if __name__ == "__main__":
    main()
