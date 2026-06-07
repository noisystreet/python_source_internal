临界区与锁 — 线程安全的基础
====================================

CPython 提供了一套 C 级别的临界区宏，用于保护共享数据的访问。

从一道题开始
------------

.. code-block:: c

    // 保护一个对象的访问
    PyObject *obj = PyList_New(0);
    Py_BEGIN_CRITICAL_SECTION(obj);
    // 安全访问 obj
    PyList_Append(obj, some_value);
    Py_END_CRITICAL_SECTION(obj);

第一问：临界区宏
---------------

临界区宏的核心实现：

.. code-block:: c

    #define Py_BEGIN_CRITICAL_SECTION(op) \
        do { \
            PyThreadState *_py_tstate = _PyThreadState_GET(); \
            PyObject *_py_op = (op); \
            if (_py_tstate != NULL) { \
                _PyCriticalSection _py_cs; \
                _PyCriticalSection_Begin(&_py_cs, _py_tstate, _py_op);

    #define Py_END_CRITICAL_SECTION() \
                _PyCriticalSection_End(&_py_cs); \
            } \
        } while (0);

在无 GIL 构建中，临界区使用对象的 ``ob_mutex`` 进行加锁。
在有 GIL 构建中，临界区自动退化为空操作。

第二问：锁的类型
---------------

CPython 3.14 内部使用多种锁：

- ``PyMutex``：轻量级互斥锁，临界区默认用它
- ``PyThread_type_lock``：平台线程锁（pthreads 或 Windows)
- 原子操作：``_Py_atomic_add``、``_Py_atomic_load`` 等

小结
----

临界区宏是无 GIL 构建下 C 扩展保证线程安全的基础工具。

通过示例脚本验证
----------------

临界区宏在 Python 层面不可见。无 GIL 构建下，C 扩展通过 ``Py_BEGIN_CRITICAL_SECTION`` / ``Py_END_CRITICAL_SECTION`` 保护共享状态。
