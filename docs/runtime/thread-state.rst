线程状态 (PyThreadState)
====================================

``PyThreadState`` 表示一个 Python 线程——每个 Python 线程对应一个。

第一问：结构
------------

.. code-block:: c

    typedef struct _ts PyThreadState;
    struct _ts {
        PyInterpreterState *interp;        // 所属解释器
        struct _ts *next;                  // 线程链表
        PyObject **dict;                   // 线程私有存储
        int recursion_depth;               // 递归深度
        PyObject *curexc_type;             // 当前异常类型
        PyObject *curexc_value;            // 当前异常值
        PyObject *curexc_traceback;        // 当前异常 traceback
        struct _frame *current_frame;      // 当前帧
        int gilstate_counter;              // GIL 获取计数
        // ...
    };

第二问：线程状态树
------------------

每个解释器有一个线程链表：

.. code-block:: text

    PyInterpreterState
    └── PyThreadState t1 → PyThreadState t2 → ...


小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - PyThreadState 存什么？
     - 当前帧、异常、GIL 计数、递归深度
   * - 线程关系？
     - 每个解释器有一个线程链表

通过示例脚本验证
----------------

运行 :file:`examples/gil_demo.py` 观察 GIL 对多线程的影响。

