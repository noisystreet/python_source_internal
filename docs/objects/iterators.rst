迭代器与生成器协议 — for 循环的底层逻辑
===========================================

在 Python 里几乎每天都在用 ``for``：

.. code-block:: python

    for x in [1, 2, 3]:
        print(x)

但你有没有想过——**``for`` 在 C 层到底是怎么执行的？** 为什么任何支持迭代的对象
（列表、文件、数据库游标……）都可以被 ``for`` 循环处理？

答案就在**迭代器协议**中。

从一道题开始
------------

试试这个：

.. code-block:: python

    >>> it = iter([1, 2, 3])
    >>> type(it)
    <class 'list_iterator'>
    >>> next(it)
    1
    >>> next(it)
    2
    >>> next(it)
    3
    >>> next(it)
    StopIteration

``iter()`` 返回一个迭代器对象，``next()`` 从它身上逐个取元素。当迭代器耗尽时，
抛出 ``StopIteration``。这就是迭代器的全部工作。

**``for`` 循环实际上就是一个 while 循环：**

.. code-block:: python

    # Python 的 for x in lst: print(x)
    # 等价于：
    it = iter(lst)           # 1. 拿到迭代器
    while True:
        try:
            x = next(it)     # 2. 每次取一个
            print(x)         # 3. 执行循环体
        except StopIteration:
            break            # 4. 耗尽就退出

.. mermaid::

    flowchart TD
        for_start["for x in lst"] --> get_iter["GET_ITER 字节码<br/>调用 lst->ob_type->tp_iter"]
        get_iter --> iter_obj["获得迭代器对象"]
        iter_obj --> for_iter["FOR_ITER 字节码<br/>调用 it->ob_type->tp_iternext"]
        for_iter --> has_next{"有下一个?"}
        has_next -->|"是: 返回对象"| body["执行循环体"]
        body --> for_iter
        has_next -->|"否: StopIteration"| end_loop["循环结束"]

第一问：迭代器协议由哪两个方法组成？
------------------------------------

迭代器协议只有两个方法，定义在 ``PyTypeObject`` 的函数指针里：

.. list-table::
   :header-rows: 1

   * - 角色
     - C 字段
     - Python 方法
     - 作用
   * - 可迭代 (iterable)
     - ``tp_iter``
     - ``__iter__()``
     - 返回一个迭代器
   * - 迭代器 (iterator)
     - ``tp_iternext``
     - ``__next__()``
     - 返回下一个值或抛 ``StopIteration``

任何类型只要实现了这两个（或其中一个）方法，就可以被 ``for`` 循环使用。

.. mermaid::

    flowchart LR
        subgraph Iterable["可迭代对象 (如 list)"]
            tp_iter["tp_iter → list_iter"]
        end
        subgraph Iterator["迭代器对象 (seqiterobject)"]
            tp_iternext["tp_iternext → iter_iternext"]
            it_index["it_index (当前位置)"]
            it_seq["it_seq (指向原始列表)"]
        end
        Iterable -->|"tp_iter 创建"| Iterator

第二问：序列迭代器 (seqiterobject) 是怎么工作的？
-------------------------------------------------

CPython 中最简单的迭代器是**序列迭代器**，用于列表、元组等序列类型。

它的 C 结构体就三个字段：

.. code-block:: c

    typedef struct {
        PyObject_HEAD
        Py_ssize_t it_index;   // 当前位置
        PyObject *it_seq;      // 指向正在迭代的序列
    } seqiterobject;

``iter_iternext`` 的实现极其简单：

.. code-block:: c

    static PyObject *
    iter_iternext(PyObject *iterator)
    {
        seqiterobject *it = (seqiterobject *)iterator;
        PyObject *seq = it->it_seq;
        PyObject *result;

        if (seq == NULL)          // 迭代器已耗尽
            return NULL;

        result = PySequence_GetItem(seq, it->it_index);
        if (result != NULL) {
            it->it_index++;       // index++
            return result;
        }
        // 取不到元素 → 说明越界了 → 标记耗尽
        Py_DECREF(seq);
        it->it_seq = NULL;
        it->it_index = -1;
        PyErr_Clear();            // 清除 IndexError
        return NULL;              // NULL 表示 StopIteration
    }

逻辑就是：**每次从序列的第 ``it_index`` 个位置取一个元素，然后 index++**。
取越界了就返回 NULL（CPython 中 NULL 等价于 Python 的 ``StopIteration``）。

第三问：for 循环的字节码长什么样？
----------------------------------

用 ``dis`` 模块看一个简单的 ``for``：

.. code-block:: python

    import dis
    dis.dis("for x in lst: print(x)")

输出大致如下：

::

    0  RESUME
    2  LOAD_NAME     lst
    4  GET_ITER          ← 调用 tp_iter 获取迭代器
    6  FOR_ITER     4 (to 18)  ← 调用 tp_iternext，停 4 步
    8  STORE_NAME    x        ← 将值赋给 x
    10 LOAD_NAME     print
    12 PUSH_NULL
    14 LOAD_NAME     x
    16 CALL          1        ← print(x)
    18 JUMP_BACKWARD 6 (to 6) ← 回到 FOR_ITER
    20 END_FOR               ← 循环结束

关键指令：

- ``GET_ITER``：调用 ``lst->ob_type->tp_iter(lst)`` 获得迭代器
- ``FOR_ITER``：调用 ``it->ob_type->tp_iternext(it)``
  - 返回非 NULL → 压入栈，继续执行循环体
  - 返回 NULL（即 ``StopIteration``）→ 跳到 ``END_FOR`` 后面的指令

.. note::

   ``FOR_ITER`` 指令内部在收到 NULL 后会 ``Py_DECREF`` 迭代器对象，所以
   ``END_FOR`` 处迭代器已经被销毁。这是 CPython 的微优化。

第四问：生成器——拥有帧的迭代器
------------------------------

**生成器函数**（含 ``yield`` 的函数）本质上也是一个迭代器。但和序列迭代器不同，
生成器迭代的数据不是从内存中的序列读取的，而是**从一个暂停的 C 帧中计算出来的**。

.. code-block:: python

    def count_up_to(n):
        i = 0
        while i < n:
            yield i
            i += 1

    gen = count_up_to(3)
    print(next(gen))  # 0
    print(next(gen))  # 1
    print(next(gen))  # 2
    print(next(gen))  # StopIteration

生成器的核心结构体是 ``PyGenObject``：

.. code-block:: c

    struct _PyGenObject {
        /* 头部 */
        PyObject_HEAD

        /* 以下由 _PyGenObject_HEAD 宏定义 */
        PyObject *gi_name;          // 生成器名称
        PyObject *gi_qualname;      // 限定名
        _PyErr_StackItem gi_exc_state; // 异常状态
        PyObject *gi_origin_or_finalizer;
        char gi_hooks_inited;
        char gi_closed;             // 是否已关闭
        char gi_running_async;      // 是否正在运行(async)
        int8_t gi_frame_state;      // 帧状态
        _PyInterpreterFrame gi_iframe; // ★ 内嵌的帧
    };

最关键的是最后那个 ``_PyInterpreterFrame gi_iframe``。

**生成器的帧是内嵌在对象中的，不分配在 C 栈上。** 当 ``yield`` 执行时，当前执行状态
（指令指针、局部变量、评估栈）全部冻结在这个帧里。下次 ``next(gen)`` 调用时，
帧被恢复，从上次暂停的位置继续执行。

.. mermaid::

    flowchart TD
        subgraph NormalFunction["普通函数"]
            call1["f()"] --> stack_frame1["在 C 栈上创建帧"]
            stack_frame1 --> execute1["执行完毕"]
            execute1 --> frame_destroyed1["帧销毁"]
        end
        subgraph Generator["生成器函数"]
            create["gen = f()"] --> heap_frame["在堆上创建帧<br/>(嵌入 PyGenObject)"]
            heap_frame --> yield1["yield 返回"]
            yield1 --> suspend["帧冻结在堆上"]
            suspend --> next["next(gen)"]
            next --> resume["帧恢复"]
            resume --> yield2["继续执行..."]
            yield2 --> suspend
        end

这就是生成器与普通函数的本质区别：

- **普通函数**：帧在 C 栈上分配，调用结束即销毁
- **生成器**：帧在堆上分配（嵌入 ``PyGenObject``），可以暂停和恢复

第五问：yield 在 C 层是什么？
-----------------------------

``yield i`` 实际上对应两条字节码指令：

::

    10 LOAD_FAST    i      ← 加载 i 到栈顶
    12 YIELD_VALUE        ← 弹出栈顶值，作为 next() 的返回值

``YIELD_VALUE`` 指令做的事情：

#. 把栈顶的值保存下来（作为 ``next()`` 的返回值）
#. 设置 ``gi_frame_state`` 为 ``FRAME_SUSPENDED``
#. 返回给调用者

当 ``next(gen)`` 再次被调用时，``CALL`` 指令最终调用了
``gen_send_ex2(gen, arg, ...)`` 函数：

.. code-block:: c

    static PySendResult
    gen_send_ex2(PyGenObject *gen, PyObject *arg, PyObject **presult,
                 int exc, int closing)
    {
        _PyInterpreterFrame *frame = &gen->gi_iframe;

        if (gen->gi_frame_state == FRAME_CREATED) {
            // 首次调用：启动生成器
            frame->state = FRAME_EXECUTING;
            *presult = _PyEval_EvalFrame(tstate, frame, ...);
        }
        else if (gen->gi_frame_state == FRAME_SUSPENDED) {
            // 恢复执行
            frame->state = FRAME_EXECUTING;
            *presult = _PyEval_EvalFrame(tstate, frame, ...);
        }
        // ...
    }

``_PyEval_EvalFrame`` 就是解释循环本身——它从帧的上次中断位置继续执行字节码。

第六问：send、throw、close 是怎么实现的？
-----------------------------------------

生成器不只是能 ``next()`` 调用，它还有三个额外的方法：

**gen.send(value)**
  把 ``value`` 作为 ``yield`` 表达式的值送进去。在 C 层，``arg`` 参数被设为一个非 NULL 值，
  然后恢复帧执行。帧中 ``YIELD_VALUE`` 指令的返回值就是 ``arg``。

.. mermaid::

    flowchart LR
        send["gen.send(100)"] --> gen_send_ex2
        gen_send_ex2 -->|"arg=100"| resume_frame["恢复帧"]
        resume_frame -->|"yield 表达式的值为 100"| continue_exec["继续执行"]

**gen.throw(exc_type)**
  在生成器内部当前暂停的位置抛出异常。``exc=1`` 标志让 ``gen_send_ex2`` 在恢复前先把异常
  设置到帧的异常状态中，这样一恢复执行就会触发 ``except`` 或传播。

**gen.close()**
  在生成器内部抛出 ``GeneratorExit`` 异常。如果生成器捕获了它并再次 ``yield``，会抛
  ``RuntimeError``。否则生成器正常结束，进入 ``FRAME_COMPLETED`` 状态。

.. code-block:: c

    // gen_close 的核心逻辑
    static PyObject *
    gen_close(PyGenObject *gen, PyObject *args)
    {
        if (gen->gi_frame_state == FRAME_SUSPENDED) {
            // 注入 GeneratorExit 异常
            _PyGen_SetStopIterationValue(...);
            gen_send_ex2(gen, Py_None, &result, 1, 1);  // exc=1, closing=1
        }
        gen->gi_frame_state = FRAME_COMPLETED;
        Py_RETURN_NONE;
    }

第七问：协程和异步生成器是什么？
--------------------------------

协程（coroutine）和异步生成器（async generator）在结构上几乎与生成器完全相同：

.. code-block:: c

    struct _PyCoroObject {
        _PyGenObject_HEAD(cr)  // 和生成器一样的头部
    };

    struct _PyAsyncGenObject {
        _PyGenObject_HEAD(ag)  // 也一样
    };

区别仅在于：

- 协程使用 ``await`` 而非 ``yield``，通过 ``__await__`` 协议等待另一个可等待对象
- 异步生成器使用 ``yield`` 但只能在 ``async def`` 内部，通过 ``__anext__`` 驱动

它们的帧机制与生成器完全一致——都是**在堆上分配的可暂停帧**。

通过示例脚本验证
----------------

运行 :file:`examples/iterator_generator_demo.py`：

.. code-block:: text

    --- 序列迭代器内部 ---
    list_iterator 的 tp_name = iterator
    每次 next() 增加 index

    --- 生成器的帧 ---
    生成器对象的 gi_frame_state = FRAME_SUSPENDED
    next(gen) → 帧恢复 → yield 值 → 帧又冻结

    --- send 方法 ---
    gen.send(100) → yield 表达式的值是 100

    --- yield from 委托 ---
    yield from [1, 2] 等价于 for x in [1, 2]: yield x

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 迭代器协议由什么组成？
     - ``tp_iter`` （获取迭代器）和 ``tp_iternext`` （取下一个值）
   * - 序列迭代器怎么工作？
     - 保存序列引用 + 下标，每次下标 +1
   * - ``for`` 循环的字节码是什么？
     - ``GET_ITER`` → ``FOR_ITER`` → 循环体 → ``JUMP_BACKWARD``
   * - 生成器与普通函数什么区别？
     - 生成器的帧在堆上（嵌入 PyGenObject），可暂停恢复
   * - ``yield`` 在 C 层做了什么？
     - ``YIELD_VALUE`` 指令保存栈顶值，冻结帧状态，返回给调用者
   * - ``send`` / ``throw`` / ``close`` 怎么实现？
     - 通过 ``gen_send_ex2`` 传入不同的 arg/exc/closing 参数
   * - 协程和生成器有什么区别？
     - 结构相同，使用 ``await`` 而非 ``yield``

下一步
------

现在你理解了迭代器和生成器的底层机制。接下来我们要进入 **内置类型** 的世界——
看看 CPython 如何实现 ``int``、``str``、``dict``、``list`` 这些每天使用的类型。
