.. _exceptions-handling:

异常处理链 — try / except / finally 的底层实现
====================================================

.. epigraph::

   "Errors are the portals of discovery."

   -- James Joyce, Ulysses


Python 的异常处理机制在 C 层由 **异常传播链** 和 **帧展开** 组成。 ``try`` / ``except`` / ``finally``
在字节码层面由 ``SETUP_FINALLY`` 、 ``PUSH_EXC_INFO`` 、 ``JUMP`` 等指令实现。

从一道题开始
------------

.. code-block:: python

    def f():
        try:
            1 / 0
        except ZeroDivisionError:
            return "caught"
        finally:
            print("cleanup")

当 ``1 / 0`` 触发 ``ZeroDivisionError`` 时，CPython 内部发生了什么？

.. mermaid::

    flowchart TD
        div["BINARY_OP '/'"] --> error["除零错误<br/>PyErr_SetString"]
        error --> lookup["在 co_exceptiontable 中<br/>查找异常处理入口"]
        lookup --> found{"找到 handler?"}
        found -->|"是"| match{"匹配 except<br/>ZeroDivisionError?"}
        match -->|"是"| exc_block["PUSH_EXC_INFO<br/>跳转到 except 块"]
        match -->|"否"| finally["执行 finally 块"]
        exc_block --> print["执行 print('cleanup')"]
        print --> return["RETURN_VALUE"]
        found -->|"否"| propagate["沿帧链向上传播<br/>frame->previous"]

第一问：异常对象的创建
----------------------

.. code-block:: c

    // Python/errors.c
    void PyErr_SetString(PyObject *type, const char *message)
    {
        PyObject *value = PyUnicode_FromString(message);
        PyErr_SetObject(type, value);
    }

    void PyErr_SetObject(PyObject *type, PyObject *value)
    {
        PyThreadState *tstate = _PyThreadState_GET();
        // 设置线程状态的异常信息
        tstate->curexc_type = type;
        tstate->curexc_value = value;
        tstate->curexc_traceback = traceback;
    }

.. mermaid::

    flowchart LR
        subgraph ThreadState["PyThreadState"]
            curexc_type
            curexc_value
            curexc_traceback
        end
        set["PyErr_SetString"] --> tstate["tstate->curexc_type = type"]
        tstate --> tstate2["tstate->curexc_value = value"]
        tstate2 --> tstate3["tstate->curexc_traceback = traceback"]

第二问：异常处理表的查找
------------------------

字节码中有异常处理表（ ``co_exceptiontable`` ），记录了 ``try`` 块的区域和处理入口。

.. code-block:: c

    // Python/ceval.c 中异常查找的简化逻辑
    int offset = (int)(instr_ptr - code->co_code_adaptive);
    PyCodeAddressRange ranges;

    // 在异常表中查找当前偏移量
    _PyCode_InitAddressRange(code, &ranges);
    while (_PyCode_NextAddressRange(&ranges)) {
        if (ranges.start <= offset && offset < ranges.end) {
            // 找到对应的 try 块
            handler = ranges.handler;
            depth = ranges.depth;  // 栈深度
            break;
        }
    }

第三问：异常在解释循环中的传播
------------------------------

.. code-block:: c

    // ceval.c 中的 error 标签
    error:
        // 1. 检查异常处理表
        PyCodeAddressRange ranges;
        _PyCode_InitAddressRange(code, &ranges);

        if (_PyCode_CheckAddressRange(&ranges, offset)) {
            // 2. 找到处理入口 → 展开栈并跳转
            int depth = ranges.depth;
            // 展开评估栈到 try 块开始时的深度
            stack_pointer = _PyFrame_GetStackPointer(frame) - depth;
            // 将异常信息推入栈
            PUSH(curexc_type);
            PUSH(curexc_value);
            PUSH(curexc_traceback);
            // 跳转到处理入口
            next_instr = handler;
            DISPATCH();
        }

        // 3. 没有处理 → 向上传播到调用者的帧
        frame->previous->instr_ptr = ...;
        tstate->current_frame = frame->previous;

通过示例脚本验证
----------------

运行 :file:`examples/exception_demo.py`：

.. code-block:: text

    --- try/except/finally 字节码 ---
    字节码显示了 SETUP_FINALLY、PUSH_EXC_INFO、JUMP 等指令

    --- 异常传播路径 ---
    内部函数未处理 → 外层 except 捕获 → 路径完整

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 异常存在哪？
     - PyThreadState 的 curexc_type / curexc_value / curexc_traceback
   * - 异常处理表在哪？
     - PyCodeObject.co_exceptiontable
   * - 传播路径？
     - 当前帧查找 → 未找到 → 沿 frame->previous 向上

参考资料
--------

- :ref:`exceptions-traceback` — Traceback 对象的构建
- :ref:`ceval-loop` — 解释循环中的异常传播路径
- :file:`Python/errors.c` — 异常处理
- :file:`Python/ceval.c` — error 标签
