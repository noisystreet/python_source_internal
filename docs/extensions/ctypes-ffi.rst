ctypes 与外部函数接口
=============================

``ctypes`` 是一个 C 扩展模块，允许 Python 直接调用 C 动态库中的函数。

第一问：ctypes 的工作原理
------------------------

``ctypes`` 在内部使用 ``dlopen`` / ``LoadLibrary`` 加载动态库，
然后通过 ``ctypes`` 的 C 级接口将函数调用转发到目标地址。

第二问：FFI 协议
---------------

.. code-block:: python

    import ctypes
    libc = ctypes.CDLL("libc.so.6")
    libc.printf(b"hello\n")  # 调用 C 函数

在 C 层，``ctypes`` 使用 ``libffi`` 库实现统一的函数调用接口。
