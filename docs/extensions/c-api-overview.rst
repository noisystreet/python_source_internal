C API 概览 — 扩展 Python 的接口
======================================

CPython 提供了一套完整的 C API，供开发者编写 Python 的 C 扩展。
这一章从高层次梳理 API 的分层体系，以及一个典型扩展模块的结构。

从一道题开始
------------

.. code-block:: c

    // 一个最简单的 C 扩展
    #include "Python.h"

    static PyObject *greet(PyObject *self, PyObject *args) {
        const char *name;
        if (!PyArg_ParseTuple(args, "s", &name))
            return NULL;
        return PyUnicode_FromFormat("Hello, %s!", name);
    }

    static PyMethodDef methods[] = {
        {"greet", greet, METH_VARARGS, "Say hello"},
        {NULL, NULL, 0, NULL}
    };

    static PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT, "hello", NULL, -1, methods,
    };

    PyMODINIT_FUNC PyInit_hello(void) {
        return PyModuleDef_Init(&moduledef);
    }

这个 25 行的 C 文件编译后，就能在 Python 中 ``import hello``。

第一问：API 分层
----------------

CPython 的 C API 分为三层，稳定性逐层提高：

.. mermaid::

    flowchart TD
        subgraph Stable_ABI["Stable ABI<br/>Py_LIMITED_API ≥ 0x030c0000"]
            api3["PyLong_FromLong<br/>PyUnicode_FromString<br/>PyObject_GetAttr"]
        end
        subgraph Limited_API["Limited API<br/>#define Py_LIMITED_API"]
            api2["PyType_FromSpec<br/>PyModule_Create<br/>PyMemberDef"]
        end
        subgraph Full_API["底层 API<br/>#include Python.h"]
            api1["PyObject 直接字段访问<br/>ob_refcnt / ob_type<br/>内部结构体"]
        end
        Stability["稳定性"] --> Full_API
        Full_API --> Limited_API
        Limited_API --> Stable_ABI

.. list-table::
   :header-rows: 1

   * - 层
     - 宏定义
     - 兼容性
   * - 底层 API
     - ``#include "Python.h"``
     - 每个小版本都可能变化
   * - Limited API
     - ``#define Py_LIMITED_API``
     - 大版本内兼容（3.x）
   * - Stable ABI
     - ``Py_LIMITED_API`` ≥ 3.x
     - 跨大版本二进制兼容（3.2 → 3.14）

第二问：扩展模块的生命周期
--------------------------

C 扩展模块从加载到卸载的完整流程：

.. mermaid::

    flowchart LR
        import["import hello"] --> finder["PathFinder 查找 hello.so"]
        finder --> dlopen["dlopen(hello.so)"]
        dlopen --> init["调用 PyInit_hello()"]
        init --> def_["PyModuleDef_Init()"]
        def_ --> add_methods["注册方法表到模块 dict"]
        add_methods --> return["返回模块对象"]
        return --> sysmod["存入 sys.modules"]

第三问：常用函数分组
--------------------

**对象创建**

.. code-block:: c

    PyObject *PyLong_FromLong(long v);
    PyObject *PyFloat_FromDouble(double v);
    PyObject *PyUnicode_FromString(const char *u);
    PyObject *Py_BuildValue(const char *fmt, ...);

**对象操作**

.. code-block:: c

    Py_INCREF(op);
    Py_DECREF(op);
    PyObject_GetAttr(obj, name);
    PyObject_SetAttr(obj, name, value);
    PyObject_CallObject(callable, args);

**类型检查**

.. code-block:: c

    PyLong_Check(op);
    PyUnicode_Check(op);
    PyList_Check(op);
    PyObject_TypeCheck(op, &PyLong_Type);

**异常处理**

.. code-block:: c

    PyErr_SetString(PyExc_TypeError, "bad arg");
    PyErr_SetObject(PyExc_ValueError, value);
    PyErr_Occurred();
    PyErr_Clear();

通过示例脚本验证
----------------

C API 在 Python 层面不可见。运行 :file:`examples/module_demo.py` 可以查看
已加载的模块信息，了解扩展模块的运行时结构。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - C API 分几层？
     - 三层：底层 API / Limited API / Stable ABI
   * - 扩展模块的入口函数是什么？
     - ``PyInit_<模块名>``
   * - 模块方法表怎么定义？
     - ``PyMethodDef`` 数组，以 ``{NULL}`` 结尾
   * - 最常用的异常设置函数？
     - ``PyErr_SetString``
