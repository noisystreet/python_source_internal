Traceback 与栈展开 — 错误信息的构建
============================================

当异常没有被捕获时，Python 会打印 Traceback——它显示异常发生时的**完整调用栈**。

从一道题开始
------------

.. code-block:: text

    Traceback (most recent call last):
      File "test.py", line 5, in <module>
        inner()
      File "test.py", line 3, in inner
        outer()
      File "test.py", line 1, in outer
        1 / 0
    ZeroDivisionError: division by zero

Traceback 展示了从异常发生点到最外层调用的完整路径。

第一问：Traceback 对象的构建
---------------------------

.. code-block:: c

    // Python/errors.c
    // 当异常在帧间传播时，构建 traceback 链
    static void add_traceback_entry(PyObject *tb, PyCodeObject *code,
                                     int lineno) {
        // 在 traceback 链表头部插入新条目
        PyTracebackObject *entry = object_new(tb);
        entry->tb_next = (PyTracebackObject *)tb;
        entry->tb_frame = frame;
        entry->tb_lineno = lineno;
        return entry;
    }

每个 ``tb_next`` 指向上层调用，形成一个链表。

第二问：栈展开
---------------

栈展开的核心是沿着 ``frame->previous`` 链向上走：

.. code-block:: c

    // 在 ceval.c 的异常传播路径中
    while (frame) {
        handler = find_handler(code, instr_ptr);
        if (handler) {
            // 找到处理入口
            break;
        }
        // 没找到，pop 帧，继续向上
        frame = frame->previous;
    }

通过示例脚本验证
---------------

运行 :file:`examples/traceback_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - Traceback 结构？
     - 链表：tb_next 指向上层
   * - 栈展开怎么走？
     - 沿 frame->previous 向上
