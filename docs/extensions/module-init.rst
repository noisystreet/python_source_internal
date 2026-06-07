模块初始化协议 — PyModuleDef
====================================

每个 C 扩展模块通过 ``PyModuleDef`` 定义模块的元数据和初始化函数。

第一问：PyModuleDef 的结构
---------------------------

.. code-block:: c

    typedef struct PyModuleDef {
        PyModuleDef_Base m_base;     // 基础结构
        const char *m_name;          // 模块名
        const char *m_doc;           // 文档字符串
        Py_ssize_t m_size;           // 模块状态大小
        PyMethodDef *m_methods;      // 模块方法表
        PyModuleDef_Slot *m_slots;   // 多阶段初始化槽
        traverseproc m_traverse;     // GC 追踪
        inquiry m_clear;             // GC 清除
        freefunc m_free;             // 析构函数
    } PyModuleDef;

第二问：模块方法表
---------------

.. code-block:: c

    static PyMethodDef foo_methods[] = {
        {"add", foo_add, METH_VARARGS, "Add two numbers"},
        {NULL, NULL, 0, NULL}
    };
