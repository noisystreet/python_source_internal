异常处理链 — try / except / finally 的底层实现
====================================================

Python 的异常处理机制在 C 层由**异常传播链**和**帧展开**组成。``try`` / ``except`` / ``finally``
在字节码层面由 ``SETUP_FINALLY``、``PUSH_EXC_INFO``、``JUMP`` 等指令实现。

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

#. ``BINARY_OP`` 指令发现除零错误，设置异常
#. 异常处理查找 ``except ZeroDivisionError`` 匹配
#. 执行 ``except`` 块
#. 然后执行 ``finally`` 块
#. 返回 "caught"

第一问：异常对象的创建
-----------------------

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

第二问：异常处理表的查找
-----------------------

字节码中有异常处理表（``co_exceptiontable``），记录了 ``try`` 块的区域和处理入口。

.. code-block:: text

    异常处理表结构 (EntryBasedCodeMap):
    start_offset → (end_offset, target_offset, depth)

    try 块的范围用字节码偏移量表示
    当异常发生时，在表中查找当前指令偏移量所在的 try 块

第三问：异常在解释循环中的传播
---------------------------

.. code-block:: c

    // ceval.c 中的 error 标签
    error:
        // 1. 检查异常处理表
        handler = _PyCode_GetExceptionHandler(code, offset);
        if (handler) {
            // 2. 找到处理入口 → 跳转
            next_instr = handler;
            stack_pointer = ...;  // 展开栈
        } else {
            // 3. 没有处理 → 向上传播
            frame->previous->instr_ptr = ...;
            tstate->current_frame = frame->previous;
            // 继续在调用者的帧中查找
        }

通过示例脚本验证
---------------

运行 :file:`examples/exception_demo.py`：

.. code-block:: text

    --- try/except/finally 字节码 ---
    try:
    1 / 0
    except ZeroDivisionError:
    return "caught"
    finally:
    print("cleanup")

    字节码显示了 SETUP_FINALLY、PUSH_EXC_INFO、JUMP 等指令

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 异常存在哪？
     - PyThreadState 的 curexc 字段
   * - 异常处理表在哪？
     - PyCodeObject.co_exceptiontable
   * - 传播路径？
     - 沿帧链向上查找异常处理入口
