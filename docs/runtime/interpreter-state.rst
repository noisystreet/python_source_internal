.. _runtime-interpreter-state:

解释器状态 (PyInterpreterState)
============================================

.. epigraph::

   "The state of your life is nothing more than a reflection of your state of mind."

   -- Wayne Dyer


``PyInterpreterState`` 表示一个 Python 解释器实例——每个子解释器对应一个。
它管理解释器级别的全局状态：小整数池、Unicode 缓存、模块缓存等。

从一道题开始
------------

.. code-block:: python

    import sys
    sys.modules  # 这个 dict 存在哪里？ → PyInterpreterState.modules

每个解释器有自己独立的 ``sys.modules`` 。子解释器之间互不干扰。

第一问：结构
------------

.. mermaid::

    flowchart LR
        subgraph PyInterpreterState["PyInterpreterState"]
            id["id → 解释器 ID"]
            ceval["ceval → GIL + eval 状态"]
            gc["gc → GC 分代状态"]
            long_state["long_state → 小整数池"]
            modules["modules → sys.modules"]
            unicode["unicode → Unicode 缓存"]
            importlib["importlib → 导入状态"]
        end

.. code-block:: c

    typedef struct _is PyInterpreterState;
    struct _is {
        int64_t id;                          // 唯一解释器 ID
        struct _ceval_state ceval;            // GIL + 评估循环状态
        struct _gc_runtime_state gc;          // 分代 GC 状态（3 代）
        struct _Py_Long_State long_state;     // 小整数池（-5 到 257）
        PyObject *modules;                    // sys.modules 字典
        PyObject *modules_by_index;           // 按索引的模块字典
        struct _Py_unicode_state unicode;     // Unicode 字符缓存
        struct _import_state importlib;       // importlib 内部状态
        // ...
    };

第二问：解释器 ID 与子解释器
-------------------------------

每个 ``PyInterpreterState`` 有一个自增的 ``id`` 字段：

.. code-block:: c

    // Python/pystate.c
    static int64_t next_id = 0;

    PyInterpreterState *PyInterpreterState_New(void) {
        PyInterpreterState *interp = alloc_interp();
        interp->id = next_id++;
        return interp;
    }

子解释器（Python 3.12+ 的 ``interp`` 模块）之间的隔离：

.. list-table::
   :header-rows: 1

   * - 数据
     - 隔离？
   * - sys.modules
     - ✅ 完全独立
   * - 内置类型 (int, str, dict)
     - ❌ 共享（全局类型对象）
   * - 小整数池
     - ✅ 每个解释器独立
   * - GC
     - ✅ 每个解释器独立
   * - GIL
     - ❌ 共享（全局 GIL）

第三问：解释器状态的初始化顺序
-------------------------------

在 ``Py_InitializeFromConfig`` 中，解释器状态按严格顺序构建：

.. mermaid::

    flowchart LR
        runtime["_PyRuntimeState_Init"] --> interp["_PyInterpreterState_New"]
        interp --> tstate["_PyThreadState_New"]
        tstate --> gil["take_gil(tstate)"]
        gil --> builtins["_Py_ReadyBuiltins(tstate)"]
        builtins --> types["_Py_ReadyTypes(tstate)"]
        types --> sys["_PySys_Init(tstate)"]

通过示例脚本验证
----------------

运行 :file:`examples/import_demo.py` 观察 ``sys.modules`` （属于当前解释器）。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - PyInterpreterState 存什么？
     - GIL、GC、小整数池、模块缓存、Unicode 状态
   * - 子解释器？
     - 每个子解释器有独立的 PyInterpreterState
   * - 哪些是子解释器共享的？
     - 内置类型、GIL（当前实现）
   * - 解释器 ID 怎么分配的？
     - 全局自增计数器

参考资料
--------

- :ref:`runtime-lifecycle` — 解释器在生命周期中的位置
- :ref:`runtime-thread-state` — 线程状态与解释器状态的关联
- :file:`Python/pystate.c` — 解释器状态管理
