.. _extensions-memory-api:

内存与对象管理 API — PyMem / PyObject
============================================

.. epigraph::

   "Measure what is measurable, and make measurable what is not so."

   -- Galileo Galilei (on memory management)


C 扩展开发中最常用到的 API。CPython 提供了两套内存分配体系：
``PyMem`` 系列（原始内存）和 ``PyObject`` 系列（对象内存）。
了解它们的区别和适用场景很重要。

从一道题开始
------------

.. code-block:: c

    // 三种分配方式，选哪个？
    void *p1 = malloc(1024);             // （1）系统 malloc
    void *p2 = PyMem_RawMalloc(1024);    // （2）CPython 原始分配
    void *p3 = PyObject_Malloc(1024);    // （3）CPython 对象分配

第一问：内存分配层级
--------------------

CPython 的内存分配器有三层：

.. mermaid::

    flowchart TD
        subgraph 应用层["应用层"]
            PyMem_RawMalloc["PyMem_RawMalloc"]
            PyObject_Malloc["PyObject_Malloc"]
            PyObject_GC_New["PyObject_GC_New"]
        end
        subgraph 分配器["分配器实现"]
            raw_alloc["系统 malloc<br/>(默认)"]
            pymalloc["pymalloc<br/>小块内存池"]
            obmalloc["obmalloc<br/>arenas + pools"]
        end
        subgraph 系统["操作系统"]
            mmap["mmap / sbrk"]
        end

        PyMem_RawMalloc --> raw_alloc
        PyObject_Malloc --> pymalloc
        pymalloc --> obmalloc
        obmalloc --> mmap
        raw_alloc --> mmap

.. list-table::
   :header-rows: 1

   * - API
     - 分配器
     - 用途
   * - ``PyMem_RawMalloc``
     - 系统 ``malloc``
     - C 库内部、小数据
   * - ``PyMem_Malloc``
     - pymalloc 池
     - 一般内存分配
   * - ``PyObject_Malloc``
     - pymalloc 池
     - Python 对象内存
   * - ``PyObject_GC_New``
     - pymalloc + GC 头
     - GC 跟踪的对象

第二问：对象创建 API
--------------------

**非 GC 对象** （普通对象，没有循环引用风险）：

.. code-block:: c

    // 分配 + 初始化
    PyObject *PyObject_Init(PyObject *op, PyTypeObject *type);
    PyVarObject *PyObject_InitVar(PyVarObject *op,
                                   PyTypeObject *type, Py_ssize_t size);

    // 合二为一的宏
    #define PyObject_New(TYPE, type) \
        ((TYPE *)PyObject_Init(_PyObject_CAST(PyObject_Malloc(sizeof(TYPE))), \
                               (type)))
    #define PyObject_NewVar(TYPE, type, size) ...

**GC 跟踪的对象** （容器对象，需要参与循环引用检测）：

.. code-block:: c

    // 分配 + 初始化 + 注册到 GC
    PyObject *PyObject_GC_New(PyTypeObject *type);
    PyObject *PyObject_GC_NewVar(PyTypeObject *type, Py_ssize_t size);

    // 手动将对象标记为 GC 跟踪
    void PyObject_GC_Track(PyObject *op);

第三问：内存分配安全实践
------------------------

.. code-block:: c

    // ✅ 扩展模块用 PyMem_RawMalloc（独立于 GIL）
    char *buf = PyMem_RawMalloc(256);

    // ✅ Python 对象用 PyObject_Malloc（和 GIL 兼容）
    PyObject *obj = PyObject_Malloc(sizeof(MyObject));

    // ❌ 混用 free 和 PyMem_Free 是未定义行为
    void *p = PyMem_Malloc(1024);
    free(p);  // 错误！应该用 PyMem_Free(p)

    // ❌ 不要在 GC 对象上手动 free
    PyObject *obj = PyObject_GC_New(&MyType);
    free(obj);  // 错误！GC 头没正确释放

通过示例脚本验证
----------------

运行 :file:`examples/obmalloc_demo.py` 观察 CPython 的内存分配行为。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 内存分配 API 分几层？
     - 三层：PyMem_Raw（系统 malloc）、PyMem（pymalloc）、PyObject（对象）
   * - GC 对象和非 GC 对象区别？
     - GC 对象需要 PyObject_GC_New + PyObject_GC_Track
   * - 混用 free 和 PyMem_Free 可以吗？
     - 不可以，必须配套使用
   * - PyMem_Raw 和 PyMem 的区别？
     - Raw 绕过 pymalloc 池，直接调用系统 malloc

参考资料
--------

- :ref:`gc-obmalloc` — pymalloc 分配器详解与 C API
- :file:`Objects/obmalloc.c` — 内存分配器
