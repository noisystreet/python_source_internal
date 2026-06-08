.. _extensions-limited-api:

Limited API 与 Stable ABI
================================

.. epigraph::

   "The price of reliability is the pursuit of the utmost simplicity."

   -- Tony Hoare


Limited API 是 CPython 3.2+ 引入的 C API 子集，保证跨版本兼容。
Stable ABI 是 Limited API 的二进制接口，一次编译可在多个 CPython 版本上运行。

从一道题开始
------------

.. code-block:: c

    // 同一个 .so 文件，可以在 Python 3.8、3.10、3.12、3.14 上运行？
    // 启用 Stable ABI 就可以：

    #define Py_LIMITED_API 0x03080000  // 最低目标版本
    #include "Python.h"

    // 限制：只能使用 Limited API 中的函数
    // 不能直接访问 PyObject 内部字段

第一问：版本宏的定义
--------------------

``Py_LIMITED_API`` 的格式是 ``0x03MMmm0000`` ：

.. code-block:: c

    #define Py_LIMITED_API 0x030c0000  // Python 3.12
    // MM = 主版本 (0c = 12), mm = 次版本 (00)

常见值：

.. list-table::
   :header-rows: 1

   * - 宏值
     - 对应版本
     - 说明
   * - ``0x03020000``
     - 3.2
     - Limited API 引入
   * - ``0x03090000``
     - 3.9
     - Vectorcall 加入
   * - ``0x030c0000``
     - 3.12
     - Py_NewRef / Py_XNewRef 加入
   * - ``0x030d0000``
     - 3.13
     - PyMutex 加入

第二问：可用与不可用的函数
--------------------------

**可用的（部分列表）：**

.. code-block:: c

    PyLong_FromLong            PyLong_AsLong
    PyUnicode_FromString       PyUnicode_AsUTF8
    PyObject_GetAttr           PyObject_SetAttr
    PyList_New                 PyList_GetItem
    PyDict_New                 PyDict_SetItem
    PyModule_Create            PyType_FromSpec

**不可用的：**

.. code-block:: c

    // 所有直接访问结构体字段的操作
    Py_TYPE(op)->tp_name      // 不可用
    op->ob_refcnt             // 不可用
    Py_SIZE(op) + 1           // 不可用

    // 替代方案：通过 API 函数
    PyType_GetName(Py_TYPE(op))
    Py_REFCNT(op)             // 仅在 Limited API 3.12+
    Py_NewRef(op) / Py_XNewRef(op)

第三问：Stable ABI 的二进制兼容
-------------------------------

Stable ABI 通过定义 ABI 稳定的函数集合实现跨版本兼容。关键在于：

- 所有 Stable ABI 函数以 ``Py``/** 或 ``_Py``/** 前缀导出为动态符号
- Windows 上通过 ``python3.dll`` （非 ``python3xx.dll`` ）加载这些符号
- Linux 上通过 ``libpython3.14d.so`` 导出

.. code-block:: bash

    # 查看 .so 中使用的 Stable ABI 符号
    objdump -T my_extension.so | grep ' Py'

    # 符合 Stable ABI 的扩展可以跨版本使用
    python3.12 -c "import my_extension"  # ✅
    python3.14 -c "import my_extension"  # ✅（同一 .so）

通过示例脚本验证
----------------

Limited API 在扩展编译时生效。在 Python 层面，可以通过 ``sys.abiflags``
查看当前构建的 ABI 标志。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - Limited API 是什么？
     - C API 的子集，保证跨版本源码兼容
   * - Stable ABI 是什么？
     - Limited API 的二进制接口，跨版本 .so 兼容
   * - 怎么启用？
     - 编译时定义 ``Py_LIMITED_API``
   * - 有什么限制？
     - 不能直接访问 PyObject 内部字段
   * - 什么时候选用？
     - 需要发布预编译 .so 给不同 Python 版本的用户

参考资料
--------

- :ref:`extensions-c-api` — C API 总体概览
- :ref:`extensions-memory-api` — 内存分配器的 ABI 稳定接口
- :pep:`384` — Stable ABI
- :file:`Include/` — Limited API 声明
