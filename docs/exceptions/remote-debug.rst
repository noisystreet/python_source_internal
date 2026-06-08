调试支持 — pdb 与底层调试协议
====================================

.. epigraph::

   "Debugging is twice as hard as writing the code in the first place."

   -- Brian Kernighan


Python 的调试器（``pdb``）基于 ``sys.settrace`` 实现。这一节深入
调试器的底层工作方式——断点管理、检查点触发、交互循环。

从一道题开始
------------

.. code-block:: python

    import pdb; pdb.set_trace()

这行代码启动了一个**交互式调试会话**。底层发生了什么？

第一问：pdb 的工作流程
----------------------

.. mermaid::

    flowchart TD
        set_trace["pdb.set_trace()"] --> settrace["sys.settrace(trace_dispatch)"]
        settrace --> line_event["等待 line 事件"]
        line_event --> check{"当前行号<br/>在断点列表中?"}
        check -->|"是"| stop["Pdb.stop() → True"]
        check -->|"否"| check_all{"Pdb.stop()<br/>全部检查?"}
        check_all -->|"True"| stop
        check_all -->|"False"| skip["继续执行"]
        stop --> cmd_loop["cmdloop()<br/>交互式命令"]
        cmd_loop --> user_cmd["用户输入 n/s/c/q"]
        user_cmd --> line_event

核心实现：

.. code-block:: python

    # Lib/bdb.py（简化）
    class Bdb:
        def trace_dispatch(self, frame, event, arg):
            if event == 'line':
                # 检查当前行是否有断点
                if self.break_here(frame):
                    return self.dispatch_line(frame)
            return self.trace_dispatch  # 返回自身，保持追踪

        def break_here(self, frame):
            # 比较文件名 + 行号
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            return (filename, lineno) in self.breaks

第二问：断点的 C 层存储
------------------------

在 C 层，``sys.settrace`` 设置的是 ``PyThreadState.c_tracefunc``：

.. code-block:: c

    // Python/sysmodule.c
    static PyObject *sys_settrace(PyObject *self, PyObject *args) {
        PyObject *func;
        if (!PyArg_ParseTuple(args, "O:settrace", &func))
            return NULL;

        PyThreadState *tstate = _PyThreadState_GET();

        // 设置追踪函数
        tstate->c_tracefunc = func;

        // 递归设置所有子线程的追踪函数
        for (PyThreadState *ts = tstate->interp->tstates_head;
             ts != NULL; ts = ts->next) {
            ts->c_tracefunc = func;
        }

        Py_RETURN_NONE;
    }

当 ``c_tracefunc`` 非空时，ceval 循环在每条指令前检查：

.. code-block:: c

    // ceval.c 中 dispatch 前的检查
    if (tstate->c_tracefunc != NULL) {
        // 构造帧对象
        PyObject *frame_obj = _PyFrame_GetFrameObject(frame);
        int event = (opcode == CALL_FUNCTION) ? PyTrace_CALL : PyTrace_LINE;

        // 调用追踪函数
        res = tstate->c_tracefunc(tstate->c_traceobj, frame_obj, event, arg);
        if (res == NULL) {
            goto error;  // 追踪函数抛异常
        }
    }

第三问：性能影响
----------------

启用追踪后性能下降显著——每条字节码都需检查：

.. list-table::
   :header-rows: 1

   * - 场景
     - 约性能
   * - 无追踪
     - 100%
   * - sys.settrace（line 事件）
     - ~ 5-10%
   * - sys.settrace（opcode 事件）
     - ~ 1-2%

通过示例脚本验证
----------------

运行 :file:`examples/debug_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - pdb.set_trace() 做了什么？
     - 调用 sys.settrace 设置回调
   * - 断点怎么存储？
     - Python 层的 dict（文件名 → 行号集合）
   * - C 层追踪存放在哪？
     - PyThreadState.c_tracefunc
   * - 调试对性能的影响？
     - line 事件约 5-10%，opcode 事件约 1-2%

参考资料
--------

- :file:`Lib/bdb.py` — pdb 底层
- :file:`Lib/pdb.py` — pdb 交互
