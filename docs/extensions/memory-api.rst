内存与对象管理 API — PyMem / PyObject
============================================

C 扩展开发中最常用到的 API。

第一问：内存分配 API
---------------

.. code-block:: c

    // 系统 malloc 包装
    void *PyMem_RawMalloc(size_t n);
    void *PyMem_RawCalloc(size_t nelem, size_t elsize);
    void PyMem_RawFree(void *p);

    // 对象内存分配
    PyObject *PyObject_Malloc(size_t n);
    void PyObject_Free(void *p);

第二问：对象创建 API
---------------

.. code-block:: c

    // 普通对象
    PyObject *PyObject_Init(PyObject *op, PyTypeObject *type);
    PyObject *PyObject_InitVar(PyVarObject *op, PyTypeObject *type,
                                Py_ssize_t size);

    // GC 跟踪的对象
    PyObject *PyObject_GC_New(PyTypeObject *type);
    PyObject *PyObject_GC_NewVar(PyTypeObject *type, Py_ssize_t size);
