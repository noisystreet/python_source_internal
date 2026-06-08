.. _runtime-thread-state:

线程状态 (PyThreadState)
====================================

.. epigraph::

   "A house divided against itself cannot stand."

   -- Abraham Lincoln (on threads in a process)


``PyThreadState`` 表示一个 Python 线程——每个 Python 线程对应一个。
它保存了线程局部的运行时状态：当前帧、异常信息、递归深度等。

从一道题开始
------------

.. code-block:: python

    import threading, sys

    def f():
        print(threading.current_thread())  # 线程的 PyThreadState

    t = threading.Thread(target=f)
    t.start()

每个 Python 线程都有自己的 ``PyThreadState``，互不共享。

第一问：结构
------------

.. mermaid::

    flowchart LR
        subgraph PyThreadState["PyThreadState"]
            interp["interp → 所属解释器"]
            next_["next → 线程链表"]
            curexc["curexc_type/value/tb → 当前异常"]
            frame["current_frame → 当前帧"]
            recursion["recursion_depth → 递归深度"]
            gil_cnt["gilstate_counter → GIL 计数"]
        end

.. code-block:: c

    typedef struct _ts PyThreadState;
    struct _ts {
        PyInterpreterState *interp;        // 所属解释器
        struct _ts *next;                  // 解释器线程链表

        // 异常信息（当前正在处理的异常）
        PyObject *curexc_type;
        PyObject *curexc_value;
        PyObject *curexc_traceback;

        struct _frame *current_frame;      // 当前执行帧

        // 递归与 GIL
        int recursion_depth;               // 递归深度（默认 1000）
        int gilstate_counter;              // GIL 获取计数
        int py_recursion_remaining;        // 剩余递归次数

        // 追踪与调试
        Py_tracefunc c_tracefunc;          // sys.settrace 回调
        PyObject *c_traceobj;              // 追踪回调的参数

        // 线程私有存储
        PyObject **dict;                   // threading.local
        uint64_t id;                       // 线程 ID
    };

第二问：线程状态树
------------------

每个解释器有一个线程链表，通过 ``next`` 指针连接：

.. mermaid::

    flowchart TD
        interp["PyInterpreterState"] --> t1["PyThreadState t1<br/>(主线程)"]
        t1 --> t2["PyThreadState t2<br/>(线程 A)"]
        t2 --> t3["PyThreadState t3<br/>(线程 B)"]

创建新线程时，CPython 在 C 层执行：

.. code-block:: c

    // Python/pystate.c
    PyThreadState *PyThreadState_New(PyInterpreterState *interp) {
        PyThreadState *tstate = alloc_tstate();
        tstate->interp = interp;

        // 插入到解释器线程链表头部
        tstate->next = interp->tstates_head;
        interp->tstates_head = tstate;

        return tstate;
    }

第三问：线程状态切换
--------------------

当 CPU 在不同 Python 线程间切换时，CPython 更新全局指针指向当前线程：

.. code-block:: c

    // Python/pystate.c
    void PyThreadState_Swap(PyThreadState *new_tstate) {
        PyThreadState *old = _PyRuntime.tstate_current;

        // 保存旧线程的帧指针
        if (old != NULL)
            old->current_frame = _PyEval_GetFrame();

        // 切换到新线程
        _PyRuntime.tstate_current = new_tstate;

        // 恢复新线程的帧
        if (new_tstate != NULL)
            _PyEval_RestoreFrame(new_tstate->current_frame);
    }

这个切换发生在：
- 显式调用 ``threading.Thread.start()`` 时
- GIL 释放后被其他线程抢占时

通过示例脚本验证
----------------

运行 :file:`examples/gil_demo.py` 观察 GIL 对多线程的影响。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - PyThreadState 存什么？
     - 当前帧、异常、GIL 计数、递归深度、追踪回调
   * - 线程关系？
     - 每个解释器有一个单向链表
   * - 线程切换怎么做？
     - PyThreadState_Swap 保存/恢复帧指针
   * - Python 线程怎么创建的？
     - PyThreadState_New → 插入解释器线程链表

参考资料
--------

- :ref:`runtime-interpreter-state` — 解释器状态、线程状态、帧栈的关系
- :ref:`ceval-loop` — 线程状态中的 current_frame 与执行循环
- :file:`Python/pystate.c` — 线程状态管理
