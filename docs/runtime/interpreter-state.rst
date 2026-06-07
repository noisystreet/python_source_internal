解释器状态 (PyInterpreterState)
============================================

``PyInterpreterState`` 表示一个 Python 解释器实例——每个子解释器对应一个。

第一问：结构
------------

.. code-block:: c

    typedef struct _is PyInterpreterState;
    struct _is {
        int64_t id;                          // 解释器 ID
        struct _ceval_state ceval;            // ceval 状态（含 GIL）
        struct _gc_runtime_state gc;          // GC 状态
        struct _Py_Long_State long_state;     // 小整数池
        PyObject *modules;                    // sys.modules 字典
        PyObject *modules_by_index;           // 按索引的模块字典
        struct _Py_unicode_state unicode;     // Unicode 状态
        // ...
    };


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

通过示例脚本验证
----------------

运行 :file:`examples/import_demo.py` 观察 ``sys.modules`` （属于当前解释器）。

