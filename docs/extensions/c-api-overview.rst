C API 概览 — 扩展 Python 的接口
======================================

CPython 提供了一套完整的 C API，供开发者编写 Python 的 C 扩展。

第一问：API 分层
---------------

.. list-table::
   :header-rows: 1

   * - 层
     - 头文件
     - 稳定性
   * - 底层 API
     - ``Python.h``
     - 随版本变化
   * - Limited API
     - ``Python.h -DPy_LIMITED_API``
     - 跨版本兼容
   * - Stable ABI
     - ``Python.h`` + ``Py_LIMITED_API`` 3.x
     - 二进制兼容

第二问：常用函数
-----------

.. code-block:: c

    // 对象创建
    PyObject *PyLong_FromLong(long v);
    PyObject *PyUnicode_FromString(const char *u);

    // 对象操作
    Py_INCREF(op);
    Py_DECREF(op);
    PyObject_GetAttr(obj, name);
