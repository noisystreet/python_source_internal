引用计数 —— 谁在用我？
========================

.. epigraph::

   "Memory is the canvas of computation."

   -- Chuck Thacker, ACM Turing Award Lecture


在 PyObject 篇我们看到了每个对象头部都有一个 ``ob_refcnt`` 字段。这一节我们就来
深入这个计数器——它如何决定一个对象的生死，以及在多线程时代遇到了什么挑战。

从一道题开始
------------

试试这段代码：

.. code-block:: python

    import sys

    a = []
    b = a
    print(sys.getrefcount(a))  # 输出多少？

答案是 **3**，不是 2。因为 ``sys.getrefcount(a)`` 传入参数时又产生了一次临时引用。

**如果把 ``b`` 删了会怎样？**

.. code-block:: python

    del b
    # a 的引用计数变回 1，对象仍然存活

    del a
    # 引用计数变为 0，列表对象被回收

CPython 就是用这个简单的计数器来管理内存的：**有人用就不回收，没人用就立刻回收** 。

.. mermaid::

    flowchart LR
        a["a"] --> listobj["列表对象 [1,2,3]"]
        b["b"] --> listobj
        listobj -->|"ob_refcnt = 2"| cnt["有 2 个引用"]

第一问：Py_INCREF 和 Py_DECREF 到底做了什么？
---------------------------------------------

在 C 层，引用计数的操作极其简单：

.. code-block:: c

    // 增加引用计数
    #define Py_INCREF(op) ((op)->ob_refcnt++)

    // 减少引用计数，如果到 0 就回收
    #define Py_DECREF(op) \
        if (--(op)->ob_refcnt == 0) \
            _Py_Dealloc(op)

CPython 在背后默默插入了大量的 ``Py_INCREF`` / ``Py_DECREF`` 调用。举个具体的例子：

.. code-block:: python

    x = obj          # Py_INCREF(obj)
    func(x)          # 传参时 Py_INCREF, 返回后 Py_DECREF
    del x            # Py_DECREF(obj)

每一个赋值、传参、返回、容器操作，背后都有这两个宏的身影。

但等等——上面的代码是简化版。实际上 ``Py_INCREF`` 的实现要复杂得多，因为要考虑 immortal 对象。

第二问：Immortal 对象如何跳过计数？
----------------------------------------

我们在 PyObject 篇已经看到，immortal 对象的引用计数是 ``0xFFFFFFFF`` （32 位全 1）。
实际 ``Py_INCREF`` 的代码比看起来复杂：

.. code-block:: c

    static inline void Py_INCREF(PyObject *op)
    {
        // 64 位系统：检查高 32 位是否 ≥ 2^31
        if (op->ob_refcnt >= _Py_IMMORTAL_INITIAL_REFCNT) {
            return;  // immortal，什么都不做！
        }
        op->ob_refcnt++;
    }

这就是为什么小整数和 ``None`` 被引用再多也不会触发实际的增减操作。

.. mermaid::

    flowchart TD
        inc["Py_INCREF(obj)"] --> check{"ob_refcnt >= 2^31?"}
        check -->|"是 (immortal)"| skip["直接返回"]
        check -->|"否 (普通对象)"| do_inc["ob_refcnt++"]
        skip --> done["结束"]
        do_inc --> check_zero["ob_refcnt == 0?"]
        check_zero -->|"是"| dealloc["_Py_Dealloc(obj)"]
        check_zero -->|"否"| done

第三问：什么时候对象会被真正回收？
----------------------------------

当 ``Py_DECREF`` 把引用计数减到 0 时，``_Py_Dealloc`` 被调用：

.. code-block:: c

    void _Py_Dealloc(PyObject *op)
    {
        // 找到类型的析构函数
        destructor dealloc = Py_TYPE(op)->tp_dealloc;

        // 释放对象自身占用的内存
        dealloc(op);
    }

不同类型的 ``tp_dealloc`` 实现不同：

- **整数** ：小整数是 immortal，不会被回收；大整数直接 ``free()``
- **列表** ：先 ``Py_DECREF`` 每个元素（让元素们有机会被回收），再 ``free()`` 列表自身
- **字典** ：同理，先释放所有键值对，再释放字典结构

.. warning::

   循环引用是一个经典问题：A 引用了 B，B 也引用了 A，但外部已经没有变量指向它们了。
   这时引用计数永远不会降到 0。CPython 的解决方案是**分代垃圾回收器** （我们会在后面的章节讲到）。

第四问：Py_INCREF 和 Py_DECREF 在哪里被调用？
-----------------------------------------------

我们追踪一段代码：``lst.append(obj)``

.. mermaid::

    flowchart TD
        python["Python: lst.append(obj)"] --> c["list_append (C 函数)"]
        c --> inc["Py_INCREF(obj)  ← 列表增加了一个引用"]
        inc --> store["存入 ob_item 数组"]
        store --> done["返回 None (Py_RETURN_NONE)"]

再看 ``lst.pop()`` ：

.. mermaid::

    flowchart TD
        python["Python: lst.pop()"] --> c["list_pop (C 函数)"]
        c --> get["从 ob_item 数组取出最后一个"]
        get --> dec["Py_DECREF(obj)  ← 列表释放了一个引用"]
        dec --> return_obj["返回取出的对象"]

这也是为什么 Python 里**所有变量都是引用**——赋值、传参、容器操作背后，
CPython 自动管理引用计数，开发者不需要手动 ``malloc`` / ``free`` 。

第五问：多线程下的引用计数——从 GIL 到 BRC
------------------------------------------

有 GIL 的传统构建
^^^^^^^^^^^^^^^^^^

在有 GIL 的 CPython 中，引用计数的操作是安全的——因为 GIL 保证同一时刻只有一个线程在
执行 Python 字节码，所以 ``ob_refcnt++`` 不会发生数据竞争。

但问题来了：**即使 GIL 保证了 Python 代码的线程安全，C 扩展中的 ``Py_INCREF`` 调用是原子的吗？**

在 64 位系统上，对 ``uint32_t`` 的读写本身就是原子的（对齐访问），所以是安全的。
但 GIL 仍然存在，所以大部分引用计数操作实际上不需要原子指令。

自由线程构建 (``--disable-gil``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

当 GIL 被移除后，事情变得复杂了。如果两个线程同时执行 ``Py_INCREF``，普通的 ``++`` 操作
会导致数据竞争。

CPython 3.14 的解决方案是 **平衡引用计数（BRC, Biased Reference Counting）** 。

核心思想：**每个对象有一个"主线程"（owning thread），本地计数走快速路径，跨线程计数走慢速路径** 。

回忆自由线程下的 PyObject 头部：

.. code-block:: c

    struct _object {
        uintptr_t ob_tid;          // 主线程 ID（谁拥有这个对象）
        uint16_t ob_flags;
        PyMutex ob_mutex;          // 对象锁
        uint8_t ob_gc_bits;
        uint32_t ob_ref_local;     // 本地引用计数（由主线程独占）
        Py_ssize_t ob_ref_shared;  // 共享引用计数（原子操作）
        PyTypeObject *ob_type;
    };

实际引用计数 = ``ob_ref_local + ob_ref_shared`` 。

- **主线程** 调用 Py_INCREF -> 直接 ``ob_ref_local++`` （非原子，快）
- **其他线程** 调用 Py_INCREF -> ``ob_ref_shared++`` （原子操作，慢）

.. mermaid::

    flowchart TD
        subgraph ThreadMain["主线程"]
            inc_local["ob_ref_local++<br/>（非原子，1 条指令）"]
        end
        subgraph ThreadOther["其他线程"]
            inc_shared["ob_ref_shared += 1<<2<br/>（原子 CAS，慢）"]
        end
        inc_local --> done
        inc_shared --> done

**合并（Merge）** ：当主线程的本地计数降到 0 时，需要把共享计数合并回来：

.. code-block:: c

    // 伪代码：_Py_MergeZeroLocalRefcount 的逻辑
    if (ob_ref_local == 0) {
        ob_ref_local = ob_ref_shared >> 2;  // 合并共享计数
        ob_ref_shared = 0;
        ob_tid = 0;  // 放弃所有权
    }

这个机制的好处是：**大多数引用计数操作发生在同一个线程内** （因为对象通常由创建它的线程使用），
所以绝大部分 ``Py_INCREF`` / ``Py_DECREF`` 走的都是本地快路径。

.. note::

   BRC 是 CPython 3.12+ 自由线程构建中的核心性能优化。它让引用计数在无 GIL 环境下的
   开销大幅降低——本地计数操作与有 GIL 时一样快。

第六问：引用计数的陷阱
----------------------

**1. 循环引用**

最简单的例子：

.. code-block:: python

    class Node:
        def __init__(self):
            self.next = None

    a = Node()
    b = Node()
    a.next = b  # b 的 refcount = 2 (a.next + b)
    b.next = a  # a 的 refcount = 2 (b.next + a)
    del a       # a 的 refcount = 1 (b.next 还指着)
    del b       # b 的 refcount = 1 (a.next 还指着)
    # 两个对象都泄漏了！

这就是 GC（垃圾回收器）存在的理由——它专门处理这种循环引用。

**2. 延迟销毁的危险**

在前面提到的 ``Py_DECREF`` 代码里，如果一个对象的引用计数降到 0，其 ``tp_dealloc``
会被调用。而这个析构函数可能触发任意 Python 代码（比如 ``__del__`` 方法）。

这就是为什么 CPython 提供了 ``Py_CLEAR`` 宏——**先置空指针，再减引用计数** ：

.. code-block:: c

    // 安全的做法
    #define Py_CLEAR(op) \
        do { \
            PyObject *_tmp = op; \
            op = NULL;          // 先置空
            Py_DECREF(_tmp);   // 再减计数
        } while (0)

如果不这么做，析构函数中的代码可能会再次访问到即将被销毁的对象，导致段错误。

通过示例脚本验证
----------------

运行 :file:`examples/refcount_demo.py`：

.. code-block:: python

    # 观察引用计数变化
    a = []
    print(sys.getrefcount(a))  # 2 (a + 临时引用)

    b = a
    print(sys.getrefcount(a))  # 3

    del b
    print(sys.getrefcount(a))  # 2

    # 容器引用的影响
    lst = [a]
    print(sys.getrefcount(a))  # 3 (a + lst[0] + 临时引用)

    # Immortal 对象
    print(sys.getrefcount(None))   # 一个巨大的数
    print(sys.getrefcount(42))     # 同上

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 引用计数怎么工作？
     - ``Py_INCREF`` 加 1，``Py_DECREF`` 减 1，到 0 就回收
   * - Immortal 怎么跳过？
     - 引用计数 ≥ 2^31 时，INC/DEC 直接返回
   * - 有 GIL 时引用计数安全吗？
     - 安全，GIL 保证了互斥
   * - 自由线程下呢？
     - BRC：本地计数（快）+ 共享计数（原子操作）
   * - 循环引用怎么办？
     - 引用计数无法处理，需要分代 GC
   * - ``Py_CLEAR`` 为什么必要？
     - 先置空指针再 DECREF，防止段错误


参考资料
--------

- :pep:`683` — 永生对象
- :pep:`703` — 自由线程与平衡引用计数（BRC）
- :file:`Include/refcount.h` — ``Py_INCREF`` / ``Py_DECREF`` 实现
- :file:`Include/object.h` — ``ob_refcnt`` 与 ``ob_refcnt_shared`` 字段

下一步
------

现在我们理解了引用计数决定对象的生死。下一篇将介绍**函数与代码对象**——
Python 中函数调用的核心，也是连接对象模型与字节码执行引擎的桥梁。
