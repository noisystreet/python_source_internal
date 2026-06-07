多阶段初始化 — PEP 489
==============================

PEP 489 引入了多阶段（multi-phase）模块初始化，允许模块在子解释器中安全使用。

第一问：单阶段 vs 多阶段
-----------------------

.. code-block:: c

    // 单阶段（旧）
    PyMODINIT_FUNC PyInit_foo(void) {
        return PyModule_Create(&foo_module);
    }

    // 多阶段（新）
    PyMODINIT_FUNC PyInit_foo(void) {
        return PyModuleDef_Init(&foo_module);
    }

第二问：执行阶段
---------------

多阶段初始化的三个阶段：

#. ``Py_mod_create``：创建模块对象
#. ``Py_mod_exec``：执行模块初始化代码
#. 子解释器导入时重复第 2 步

.. code-block:: c

    static PyModuleDef_Slot foo_slots[] = {
        {Py_mod_create, create_foo},
        {Py_mod_exec, exec_foo},
        {0, NULL}
    };
