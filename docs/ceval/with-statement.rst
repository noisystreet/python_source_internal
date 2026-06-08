with 语句的底层实现 — 上下文管理协议
===========================================

.. epigraph::

   "Enter by the narrow gate; for the gate is wide and the way is easy that leads to destruction."

   -- Matthew 7:13 (on entering and exiting)


``with`` 语句是 Python 的上下文管理语法糖。在 C 层，它对应
字节码 ``SETUP_WITH``、``WITH_EXCEPT_START`` 和 ``POP_BLOCK``。

从一道题开始
------------

.. code-block:: python

    with open("file.txt") as f:
        f.read()

这个语句展开为：

.. code-block:: text

    f = open("file.txt").__enter__()
    # 执行 f.read()
    # 无论如何 → f.__exit__(...)

在字节码层面：

.. code-block:: text

    0  RESUME
    2  LOAD_NAME     open
    4  LOAD_CONST    "file.txt"
    6  CALL          1
    8  BEFORE_WITH              ← 调用 __enter__，保存 __exit__
    10 STORE_NAME    f          ← f = __enter__() 的结果
    12 LOAD_NAME     f
    14 LOAD_ATTR     read
    16 CALL          0
    18 POP_TOP
    20 LOAD_CONST    None
    22 LOAD_NAME     f
    24 CALL_METHOD   2          ← f.__exit__(None, None, None)
    26 POP_TOP
    28 RETURN_VALUE

第一问：BEFORE_WITH 指令
--------------------------

``BEFORE_WITH`` 是 ``with`` 语句的入口指令：

.. code-block:: c

    // Python/ceval.c — BEFORE_WITH 实现（简化）
    case TARGET(BEFORE_WITH): {
        PyObject *obj = TOP();  // 上下文管理器对象
        PyObject *enter = PyObject_GetAttr(obj, &_Py_ID(__enter__));
        PyObject *exit  = PyObject_GetAttr(obj, &_Py_ID(__exit__));

        // 调用 __enter__
        PyObject *result = PyObject_CallNoArgs(enter);

        // 将 __exit__ 推入栈底（异常发生时使用）
        PUSH(exit);

        // 栈顶是 __enter__ 的返回值
        PUSH(result);
        DISPATCH();
    }

指令执行后的栈状态：

.. mermaid::

    flowchart LR
        subgraph before["BEFORE_WITH 之前"]
            stack1["栈<br/>(栈顶) obj"]
        end
        subgraph after["BEFORE_WITH 之后"]
            stack2["栈<br/>(栈顶) __enter__ 返回值<br/>__exit__ 函数<br/>... 下层"]
        end

第二问：异常发生时的处理
------------------------

当 ``with`` 块内发生异常时，解释器检查异常处理表，跳转到清理代码：

.. code-block:: c

    // ceval.c — with 块的异常处理（简化）
    case TARGET(WITH_EXCEPT_START): {
        // 栈顶是 __exit__、异常信息
        PyObject *exit_func = PEEK(3);   // __exit__
        PyObject *exc_type = PEEK(2);
        PyObject *exc_val  = PEEK(1);
        PyObject *exc_tb   = TOP();

        // 调用 __exit__(exc_type, exc_val, exc_tb)
        PyObject *result = PyObject_CallFunctionObjArgs(
            exit_func, exc_type, exc_val, exc_tb, NULL);

        if (result == Py_True) {
            // __exit__ 返回 True → 抑制异常
            PyErr_Clear();
        }
        // 返回 False 或不返回 → 继续传播异常
    }

第三问：PEP 343 — 上下文管理协议
----------------------------------

``with`` 语句的设计最早在 PEP 343 中定义。协议只有两个方法：

.. code-block:: python

    class MyContext:
        def __enter__(self):
            # 进入 with 块时调用
            return self  # 返回值赋给 as 变量

        def __exit__(self, exc_type, exc_val, exc_tb):
            # 离开 with 块时调用（无论是否异常）
            # 返回 True 抑制异常，False 或 None 传播异常
            return False

C 层面的检查：

.. code-block:: c

    // BEFORE_WITH 执行时的类型检查（Objects/abstract.c）
    int PyObject_CheckContext(PyObject *obj) {
        // 检查是否有 __enter__ 和 __exit__ 方法
        PyObject *enter = PyObject_GetAttr(obj, &_Py_ID(__enter__));
        PyObject *exit  = PyObject_GetAttr(obj, &_Py_ID(__exit__));
        if (enter == NULL || exit == NULL) {
            // 缺少任一方法 → 不是有效的上下文管理器
            return 0;
        }
        return 1;
    }

通过示例脚本验证
----------------

运行 :file:`examples/with_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - with 语句的核心字节码？
     - BEFORE_WITH → __enter__ → ... → __exit__ 调用
   * - __exit__ 存在哪？
     - 在 BEFORE_WITH 时被推入评估栈
   * - 异常怎么传递给 __exit__？
     - WITH_EXCEPT_START 指令从栈中取出异常信息
   * - __exit__ 返回 True 意味着什么？
     - 抑制异常（PyErr_Clear）
   * - 不是上下文管理器会怎样？
     - BEFORE_WITH 检查 __enter__/__exit__ 属性，缺一即报错

参考资料
--------

- :pep:`343` — with 语句
- :file:`Python/ceval.c` — BEFORE_WITH / WITH_EXCEPT_START
