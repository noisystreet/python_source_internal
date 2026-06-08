多阶段初始化 — PEP 489
==============================

.. epigraph::

   "We must learn to live together as brothers or perish together as fools."

   -- Martin Luther King Jr. (on sub-interpreter coexistence)


PEP 489 引入了多阶段（multi-phase）模块初始化，允许模块在子解释器中安全使用。
它是现代 C 扩展模块初始化的推荐方式。

从一道题开始
------------

.. code-block:: c

    // 旧方式（单阶段）：模块在进程全局只有一份状态
    PyMODINIT_FUNC PyInit_foo(void) {
        return PyModule_Create(&foo_module);
    }

    // 新方式（多阶段）：每个子解释器创建独立的状态
    PyMODINIT_FUNC PyInit_foo(void) {
        return PyModuleDef_Init(&foo_module);
    }

区别：``PyModule_Create`` 同时执行创建和初始化，``PyModuleDef_Init``
将两个阶段分离。

第一问：单阶段 vs 多阶段
------------------------

.. mermaid::

    flowchart TD
        subgraph 单阶段["单阶段初始化"]
            s1["PyModule_Create(&def)"] --> s2["创建模块对象"]
            s2 --> s3["注册方法表"]
            s3 --> s4["执行模块代码"]
        end

        subgraph 多阶段["多阶段初始化"]
            m1["PyModuleDef_Init(&def)"] --> m2["阶段 1: Py_mod_create<br/>创建模块对象"]
            m2 --> m3["阶段 2: Py_mod_exec<br/>执行初始化代码"]
            m3 --> m4["子解释器导入时<br/>重复阶段 2 不重复阶段 1"]
        end

第二问：PEP 489 的执行阶段
--------------------------

多阶段初始化通过 ``PyModuleDef_Slot`` 数组定义两个阶段：

.. code-block:: c

    // 1. 创建阶段：分配模块状态
    static PyObject *
    create_foo(PyObject *spec, PyModuleDef *def) {
        // 创建空模块（只分配状态，不初始化）
        PyObject *mod = PyModule_NewObject(spec, def);
        MyState *state = (MyState *)PyModule_GetState(mod);
        state->cache = NULL;  // 初始化为零
        return mod;
    }

    // 2. 执行阶段：初始化状态
    static int
    exec_foo(PyObject *mod) {
        MyState *state = (MyState *)PyModule_GetState(mod);
        state->cache = PyDict_New();  // 创建缓存
        return 0;  // 成功
    }

    // 3. 注册到模块定义
    static PyModuleDef_Slot foo_slots[] = {
        {Py_mod_create, create_foo},
        {Py_mod_exec, exec_foo},
        {0, NULL}  // 哨兵
    };

    // 4. 模块入口
    PyMODINIT_FUNC PyInit_foo(void) {
        static PyModuleDef def = {
            PyModuleDef_HEAD_INIT,
            "foo", NULL, sizeof(MyState),
            methods, foo_slots,
        };
        return PyModuleDef_Init(&def);
    }

第三问：子解释器场景
--------------------

当子解释器导入同一个模块时：

.. code-block:: python

    import _xxsubinterpreters
    interp = _xxsubinterpreters.create()

    # 子解释器中导入 foo
    _xxsubinterpreters.run_string(interp, "import foo")

多阶段初始化在子解释器中的行为：

.. mermaid::

    flowchart LR
        main["主解释器"] --> create1["Py_mod_create<br/>创建状态 A"]
        create1 --> exec1["Py_mod_exec<br/>初始化状态 A"]

        sub_interp["子解释器"] --> create2["Py_mod_create<br/>创建状态 B（独立副本）"]
        create2 --> exec2["Py_mod_exec<br/>初始化状态 B"]

        main -.- same_module["同一份 PyModuleDef<br/>不同 PyInterpreterState"]

通过示例脚本验证
----------------

多阶段初始化在扩展模块的 C 代码中体现，不在 Python 层面直接观察。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 单阶段 vs 多阶段？
     - 多阶段把创建和执行分离，支持子解释器
   * - 有几个阶段？
     - 创建 (Py_mod_create) → 执行 (Py_mod_exec)
   * - 子解释器导入时？
     - 重复执行阶段，不重复创建
   * - 为什么需要多阶段？
     - 每个子解释器获得独立的状态副本，线程安全
   * - 怎么定义阶段槽？
     - ``PyModuleDef_Slot`` 数组，以 ``{0, NULL}`` 结尾

参考资料
--------

- :pep:`489` — 多阶段初始化
