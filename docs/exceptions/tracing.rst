sys.settrace / sys.setprofile — 追踪与性能分析
====================================================

``sys.settrace`` 和 ``sys.setprofile`` 允许在代码执行时设置回调函数，
用于调试器（如 ``pdb``）和性能分析器（如 ``cProfile``）。

从一道题开始
------------

.. code-block:: python

    import sys

    def trace(frame, event, arg):
        print(f"{event}: {frame.f_code.co_name}")
        return trace

    sys.settrace(trace)

每当解释器执行一条新代码行、调用或返回函数时，都会调用这个 ``trace`` 函数。

.. mermaid::

    flowchart TD
        ceval["ceval 执行字节码"] --> check{"tstate->c_tracefunc<br/>!= NULL?"}
        check -->|"否"| normal["正常执行"]
        check -->|"是"| event{"事件类型?"}
        event -->|"call"| call["调用前触发<br/>arg = 函数对象"]
        event -->|"return"| ret["返回后触发<br/>arg = 返回值"]
        event -->|"line"| line["每行代码执行前<br/>arg = None"]
        event -->|"exception"| exc["异常发生时<br/>arg = (type, value, tb)"]
        call --> dispatch["调用 trace 函数"]
        ret --> dispatch
        line --> dispatch
        exc --> dispatch
        dispatch --> resume["恢复字节码执行"]

第一问：追踪事件的类型
-----------------------

Python 定义了以下几种追踪事件：

.. list-table::
   :header-rows: 1

   * - 事件
     - 触发时机
     - arg
   * - ``call``
     - 函数调用时
     - 函数对象
   * - ``return``
     - 函数返回时
     - 返回值
   * - ``line``
     - 执行新行时
     - 无
   * - ``exception``
     - 异常发生时
     - (exc_type, value, tb)
   * - ``opcode``
     - 执行每条字节码
     - 无

第二问：C 层的实现
------------------

在 ``ceval.c`` 中，解释循环在执行每一条指令之前检查追踪标志：

.. code-block:: c

    // ceval.c 主循环中的追踪代码
    if (tstate->c_tracefunc != NULL) {
        // 构造帧对象（延迟创建，只在需要时）
        PyObject *frame_obj = _PyFrame_GetFrameObject(frame);

        int event;
        // 判断事件类型
        if (opcode == CALL_FUNCTION) {
            event = PyTrace_CALL;
        } else if (opcode == RETURN_VALUE) {
            event = PyTrace_RETURN;
        } else {
            // 每行代码：在 DISPATCH 前检查行号变化
            event = PyTrace_LINE;
        }

        // 调用追踪函数
        if (tstate->c_tracefunc(tstate->c_traceobj, frame_obj, event, arg)) {
            // 追踪函数返回非零 → 错误
        }
    }

``sys.settrace`` 设置 ``tstate->c_tracefunc``。当这个字段非空时，
解释器在每次 ``call``、``return``、``line``、``exception`` 事件发生时
调用这个函数。

第三问：setprofile 与 settrace 的区别
--------------------------------------

.. list-table::
   :header-rows: 1

   * - 特性
     - settrace
     - setprofile
   * - 触发事件
     - call / return / line / exception
     - call / return
   * - 用于什么场景
     - 调试器（pdb 基于它）
     - 性能分析器（cProfile 基于它）
   * - 性能影响
     - 极大（每条字节码都可能触发）
     - 中等（仅函数调用时触发）

通过示例脚本验证
----------------

运行 :file:`examples/tracing_demo.py`：

.. code-block:: text

    --- 函数调用追踪 (call/return) ---
    [    call] traced_function
    [   line] traced_function:1
    [   line] traced_function:2
    [  return] traced_function

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - settrace 做了什么？
     - 设置 tstate->c_tracefunc 回调
   * - 何时触发？
     - call / return / line / exception 事件
   * - setprofile 和 settrace 的区别？
     - setprofile 只触发 call/return，用于性能分析
   * - 性能影响？
     - 启用追踪后性能显著下降（每条指令都检查）
