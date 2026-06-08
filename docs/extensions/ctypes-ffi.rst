ctypes 与外部函数接口
=============================

``ctypes`` 是一个 C 扩展模块，允许 Python 直接调用 C 动态库中的函数，
而无需编写任何 C 代码。

从一道题开始
------------

.. code-block:: python

    import ctypes
    libc = ctypes.CDLL("libc.so.6")
    libc.printf(b"Hello from libc!\n")  # 直接调用 C 函数

Python 的数据怎么传给 C？C 的返回值怎么变成 Python 对象？这背后是 ``ctypes``
的核心：**FFI（Foreign Function Interface）** 。

第一问：ctypes 的数据类型映射
------------------------------

.. list-table::
   :header-rows: 1

   * - ctypes 类型
     - C 类型
     - Python 类型
   * - ``c_int``
     - ``int``
     - ``int``
   * - ``c_float``
     - ``float``
     - ``float``
   * - ``c_double``
     - ``double``
     - ``float``
   * - ``c_char_p``
     - ``char *``
     - ``bytes`` 或 ``None``
   * - ``c_void_p``
     - ``void *``
     - ``int`` 或 ``None``
   * - ``POINTER(c_int)``
     - ``int *``
     - ``ctypes`` 指针对象

第二问：libffi 和调用流程
--------------------------

``ctypes`` 的底层使用 ``libffi`` （Foreign Function Interface）库来实现跨语言的函数调用：

.. mermaid::

    flowchart LR
        py["libc.printf(b'hello')"] --> pyd["ctypes 的 C 扩展层"]
        pyd --> prepare["libffi 准备调用：<br/>1. 设置参数类型 (cif)<br/>2. 将参数压栈"]
        prepare --> call["libffi 调用目标函数"]
        call --> c_func["C 函数执行"]
        c_func --> result["libffi 获取返回值"]
        result --> py_obj["ctypes 将 C 返回值转 Python 对象"]
        py_obj --> return["返回给调用者"]

``libffi`` 的核心 API 调用序列：

.. code-block:: c

    // ctypes 内部使用 libffi 的简化流程
    #include <ffi.h>

    // 1. 定义函数签名（ABI 描述）
    ffi_cif cif;
    ffi_type *args[] = { &ffi_type_pointer };
    ffi_prep_cif(&cif, FFI_DEFAULT_ABI, 1, &ffi_type_sint32, args);

    // 2. 设置参数
    void *values[] = { &"hello" };
    int result;

    // 3. 调用
    ffi_call(&cif, (void *)printf, &result, values);

第三问：ctypes 的内存管理
--------------------------

``ctypes`` 创建的 C 对象通过引用计数管理生命周期：

.. code-block:: python

    >>> import ctypes
    >>> p = ctypes.create_string_buffer(b"hello")
    >>> ctypes.addressof(p)
    139987654321024

    # p 被 Python 引用时，底层 C 内存不会释放
    # p 被 GC 回收时，ctypes 自动释放 C 内存

对于 ``c_char_p`` 和指针类型，ctypes 不会自动管理目标内存的生命周期——
调用者有责任确保内存的存活时间不短于指针使用时间。

通过示例脚本验证
----------------

ctypes 使用示例详见 Python 标准库文档。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - ctypes 怎么调用 C 函数？
     - 通过 ``dlopen`` 加载动态库 + ``libffi`` 实现跨语言调用
   * - 数据类型怎么映射？
     - ``c_int`` → int, ``c_char_p`` → bytes, ``c_double`` → float
   * - libffi 的核心函数？
     - ``ffi_prep_cif`` （准备签名）+ ``ffi_call`` （执行调用）
   * - ctypes 管理内存吗？
     - 管理包装对象的内存，但不管理指针指向的原始 C 内存
   * - 安全吗？
     - 不安全，调用者需保证参数类型与 C 函数签名一致

参考资料
--------

- :file:`Modules/_ctypes/` — ctypes 实现
