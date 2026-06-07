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
-----------------------

在 ``ceval.c`` 中，解释循环在执行每一条指令之前检查追踪标志：

.. code-block:: c

    // ceval.c 主循环
    if (tstate->c_tracefunc != NULL) {
        // 调用追踪函数
        if (tstate->c_tracefunc(tstate->c_traceobj, frame, event, arg)) {
            // 追踪函数返回非零 → 错误
        }
    }

``sys.settrace`` 设置 ``tstate->c_tracefunc``。当这个字段非空时，
解释器在每次 ``call``、``return``、``line``、``exception`` 事件发生时
调用这个函数。

通过示例脚本验证
---------------

运行 :file:`examples/tracing_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - settrace 做了什么？
     - 设置 tstate->c_tracefunc 回调
   * - 何时触发？
     - call / return / line / exception
   * - setprofile 和 settrace 的区别？
     - setprofile 只触发 call/return，用于性能分析
