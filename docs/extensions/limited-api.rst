Limited API 与 Stable ABI
================================

Limited API 是 CPython 3.2+ 引入的 C API 子集，保证跨版本兼容。

第一问：启用方式
---------------

.. code-block:: c

    // 编译时定义 Py_LIMITED_API
    #define Py_LIMITED_API 0x030c0000
    #include "Python.h"

第二问：限制
-----------

- 不能访问 ``PyObject`` 的内部字段（``ob_refcnt``、``ob_type``）
- 不能使用 ``Py_TYPE()`` 之外的宏
- 所有内存操作通过 API 函数进行


小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - Limited API 是什么？
     - C API 的子集，保证跨版本兼容
   * - 怎么启用？
     - 编译时定义 ``Py_LIMITED_API``
   * - 有什么限制？
     - 不能直接访问 PyObject 内部字段

通过示例脚本验证
----------------

Limited API 在扩展编译时生效，不在 Python 运行时体现。

