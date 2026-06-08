.. _extensions-module-init:

模块初始化协议 — PyModuleDef
====================================

.. epigraph::

   "Well begun is half done."

   -- Aristotle (on module initialization)


每个 C 扩展模块通过 ``PyModuleDef`` 定义模块的元数据和初始化函数。
这是 C 扩展开发者最常接触的数据结构。

从一道题开始
------------

.. code-block:: c

    // 一个典型的 C 扩展定义
    static PyModuleDef mymodule = {
        PyModuleDef_HEAD_INIT,
        "mymodule",
        "My module documentation",
        -1,
        methods,
    };

    PyMODINIT_FUNC PyInit_mymodule(void) {
        return PyModuleDef_Init(&mymodule);
    }

每个字段都有特定的含义。

第一问：PyModuleDef 的完整结构
------------------------------

.. code-block:: c

    typedef struct PyModuleDef {
        PyModuleDef_Base m_base;     // 基础结构（PyModuleDef_HEAD_INIT 填充）
        const char *m_name;          // 模块名（必须和 PyInit_ 后的名称一致）
        const char *m_doc;           // 文档字符串（__doc__）
        Py_ssize_t m_size;           // 模块状态大小（-1 = 无状态，0 = 有状态）
        PyMethodDef *m_methods;      // 模块方法表
        PyModuleDef_Slot *m_slots;   // 多阶段初始化槽（PEP 489）
        traverseproc m_traverse;     // GC 追踪回调
        inquiry m_clear;             // GC 清除回调
        freefunc m_free;             // 模块析构函数
    } PyModuleDef;

第二问：m_size 字段的含义
-------------------------

``m_size`` 控制模块是否拥有 per-module 状态：

.. code-block:: c

    // m_size = -1: 无模块状态（老式设计）
    // 模块级全局变量存储在 C 全局变量中
    // ⚠️ 在子解释器中不安全——多个解释器共享同一份全局变量
    static PyModuleDef mymodule = {
        PyModuleDef_HEAD_INIT, "mymodule", NULL, -1, methods
    };

    // m_size > 0: 有模块状态（推荐的现代写法）
    // 每个解释器得到独立的状态副本
    typedef struct {
        PyObject *my_cache;
        int my_counter;
    } MyModuleState;

    static PyModuleDef mymodule = {
        PyModuleDef_HEAD_INIT, "mymodule", NULL, sizeof(MyModuleState), methods
    };

    // 获取模块状态的宏
    #define GET_STATE(mod) \
        ((MyModuleState *)PyModule_GetState(mod))

第三问：模块方法表与 GC 回调
----------------------------

**方法表** 定义了模块级函数：

.. code-block:: c

    static PyMethodDef foo_methods[] = {
        {"add", foo_add, METH_VARARGS, "Add two numbers"},
        {"add_fast", foo_add, METH_FASTCALL, "Fast add"},
        {"version", (PyCFunction)foo_version, METH_NOARGS, "Get version"},
        {NULL, NULL, 0, NULL}           // 哨兵
    };

**GC 回调** （可选）用于模块对象参与垃圾回收：

.. code-block:: c

    static int module_traverse(PyObject *mod, visitproc visit, void *arg) {
        MyModuleState *state = GET_STATE(mod);
        Py_VISIT(state->my_cache);       // 告诉 GC 要跟踪的引用
        return 0;
    }

    static int module_clear(PyObject *mod) {
        MyModuleState *state = GET_STATE(mod);
        Py_CLEAR(state->my_cache);       // 循环引用时清空
        return 0;
    }

通过示例脚本验证
----------------

运行 :file:`examples/module_demo.py` 查看模块元数据。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - PyModuleDef 包含什么？
     - 模块名、文档、方法表、GC 回调
   * - m_size = -1 意味着什么？
     - 无 per-module 状态，子解释器不安全
   * - m_size > 0 怎么用？
     - PyModule_GetState 获取 per-module 状态指针
   * - 模块方法表是什么？
     - ``PyMethodDef`` 数组，以哨兵结尾

参考资料
--------

- :ref:`extensions-multi-phase` — 多阶段初始化与子解释器
- :ref:`extensions-dynamic-loading` — 动态加载与链接
- :ref:`modules-object` — 模块对象的 C 层结构
- :file:`Objects/moduleobject.c` — PyModule_Create
