.. _concurrency-async:

async/await 底层实现 — 协程与事件循环
============================================

.. epigraph::

   "Time is the coin of your life. It is the only coin you have, and only you can determine how it will be spent."

   -- Carl Sandburg


Python 的 ``async`` / ``await`` 语法在 C 层由 **生成器架构** 提供支持——协程
本质上就是在生成的帧上做了封装的生成器。

从一道题开始
------------

.. code-block:: python

    async def hello():
        return "hello"

    # 调用 async 函数 → 创建协程对象
    coro = hello()  # <coroutine object hello at 0x...>

第一问：协程对象
----------------

协程对象是 ``PyCoroObject``——它和生成器共享相同的帧架构：

.. code-block:: c

    typedef struct _PyCoroObject {
        PyObject_HEAD
        // 生成器通用头部
        PyObject *cr_weakreflist;
        PyObject *cr_name;
        PyObject *cr_qualname;
        _PyErr_StackItem cr_exc_state;
        char cr_running_async;
        // 嵌入的帧
        _PyInterpreterFrame cr_iframe;
    } PyCoroObject;

关键区别： ``cr_running_async`` 标志——它防止协程被重入。

第二问：await 的实现
--------------------

``await`` 在字节码层面是 ``SEND`` 指令：

.. code-block:: text

    0 LOAD_CONST 0 ('hello')
    2 RETURN_VALUE

    # await hello() 编译为：
    0 CALL         0 (hello)
    2 SEND         0
    4 RESUME       1
    6 RETURN_VALUE

``SEND`` 指令将当前协程的控制权转让给被等待的协程或可等待对象。

第三问：事件循环
----------------

事件循环不是 CPython 内核的一部分——它在标准库 ``asyncio`` 中实现。
但底层机制（ ``__await__`` 协议）由 C 层提供：

.. code-block:: c

    // PyCoro_Type 实现了 tp_as_async.am_await
    // 使得协程对象可以通过 await 语法等待

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 协程和生成器的关系？
     - 共享相同的帧架构（_PyInterpreterFrame）
   * - await 的字节码？
     - SEND 指令
   * - 协程的 C 结构？
     - PyCoroObject（内含 _PyInterpreterFrame）

通过示例脚本验证
----------------

运行 :file:`examples/async_demo.py`。

参考资料
--------

- :ref:`objects-iterators` — 生成器与协程同源
- :ref:`concurrency-free-threading` — 自由线程下的 async 并发
- :pep:`492` — async/await
- :file:`Python/ceval.c` — SEND / GEN_START
