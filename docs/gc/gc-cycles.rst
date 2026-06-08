.. _gc-cycles:

环形引用检测 — 三色标记算法
========================================

.. epigraph::

   "What goes around comes around."

   -- Proverb (on circular references)


上一节我们看到了 GC 的整体流程。这一节深入**环形引用检测的核心算法**——
CPython 使用的三色标记变体。

从一道题开始
------------

.. code-block:: text

    给定一组对象和引用关系:
    A → B → C → A  (循环)
    D → E          (无循环)
    F              (孤立)

    如何找到属于循环的 {A, B, C} 并回收它们？

答案：从全局根对象出发，标记所有可达对象。未被标记的就是不可达的。
{ A, B, C } 虽然互相引用，但从根不可达，所以被回收。

第一问：deduce_unreachable 的流程
----------------------------------

``deduce_unreachable`` 是 GC 的核心函数。它实现了三色标记：

.. mermaid::

    flowchart TD
        start["deduce_unreachable(young, unreachable)"] --> init["1. 所有对象初始化为
        GC_REFS_REACHABLE"]
        init --> update["2. 更新引用计数
        减去跨代引用"]
        update --> subtract["3. gc_refs = ob_refcnt - 来自堆外的引用"]
        subtract --> scan["4. 从 gc_refs > 0 的对象出发
        遍历引用链"]
        scan --> reachable["5. 遍历到的标记为 GC_REFS_REACHABLE"]
        reachable --> collect["6. 剩下的 gc_refs == 0 的对象
        移到 unreachable 链表"]

**第 1 步：初始化**
  所有对象设为 ``GC_REFS_REACHABLE`` 。

**第 2-3 步：计算净引用计数**
  ``gc_refs = ob_refcnt`` 减去来自"堆外"（全局变量、栈、跨代引用）的引用数。
  如果 ``gc_refs <= 0``，说明它只被堆内的其他对象引用。

**第 4-5 步：可达性传播**
  从 ``gc_refs > 0`` 的对象出发（它们一定是可达的），沿引用链遍历。
  遇到的对象标记为可达。

**第 6 步：收集**
  遍历后仍为 ``gc_refs == 0`` 的对象就是不可达循环中的对象。

第二问：为什么需要减去跨代引用？
--------------------------------

分代收集的关键优化：**收集第 N 代时，只考虑该代内部的引用** 。

如果第 2 代的对象引用了第 0 代的对象，这个引用**不计入第 0 代对象
的 gc_refs**——因为它来自堆外（被收集的堆区域之外）。

.. code-block:: c

    // 计算 gc_refs 的核心逻辑
    // visits 是一个工作列表，持有所有被跟踪的对象
    update_refs(young) {
        for (obj in young) {
            // 初始 gc_refs = ob_refcnt
            GC_SET_REFS(gc, Py_REFCNT(FROM_GC(gc)));
        }
        // 减去来自堆外的引用
        subtract_refs(young);
    }

    subtract_refs(young) {
        for (obj in young) {
            // 对 obj 的每个引用者
            for (referrer in get_referrers(obj)) {
                if (referrer not in young) {
                    // 引用来自堆外 → 减 1
                    gc_refs--;
                }
            }
        }
    }

第三问：为什么不能只靠引用计数找环？
-------------------------------------

你可能会想："为什么不直接找 gc_refs 为 0 的对象？"

因为**循环引用中的所有对象引用计数都不为 0**——它们互相引用。
A 指向 B 使 B 的引用计数 +1，B 指向 A 使 A 的引用计数 +1。

但减去跨代引用后，如果 A 和 B 都不被外部引用，它们的 ``gc_refs`` 都会降到 0。
这就是算法能检测循环引用的原因。

第四问：GC 头部的结构
-----------------------

每个被跟踪的对象都有一个 ``PyGC_Head`` 嵌入在对象头部和 ``PyObject_HEAD``
之间：

.. code-block:: c

    // pycore_gc.h
    typedef struct {
        PyGC_Head _gc_head;  // 嵌入 GC 链表节点
        PyObject_HEAD        // 标准对象头部
        // ... 类型特定字段 ...
    } GCObject;

    // PyGC_Head 结构
    typedef union _gc_head {
        struct {
            union _gc_head *gc_next;    // 链表前向指针
            union _gc_head *gc_prev;    // 链表后向指针（低位存标记位）
            Py_ssize_t gc_refs;         // GC 引用计数
        } gc;
        double dummy;  // 确保对齐
    } PyGC_Head;

``gc_prev`` 的低位用于存储标记位：

- 最低位：``_PyGC_PREV_MASK_COLLECTING`` — 正在收集中
- ``gc_refs`` ：可以是 ``GC_REFS_REACHABLE`` 、``GC_REFS_TENTATIVELY_UNREACHABLE``
  或实际的引用计数值

第五问：处理 __del__ 和弱引用
-------------------------------

如果不可达对象中有 ``__del__`` 方法（或 C 层面的 ``tp_del`` ），事情变得复杂：

.. code-block:: c

    // 将不可达对象中的 legacy finalizer 对象移到 finalizers 链表
    move_legacy_finalizers(&unreachable, &finalizers);

    // 从 finalizer 对象可达的对象也一起保留
    move_legacy_finalizer_reachable(&finalizers);

这些对象不会被回收——因为 ``__del__`` 可能复活对象（让其他对象重新引用它）。
CPython 将这些对象移到 ``gc.garbage`` 列表中，由开发者手动处理。

.. note::

   Python 3.14 改进了 legacy finalizer 的处理策略。只有定义了 ``tp_del``
   （而不是 ``tp_finalize`` ）的对象才会被移到 ``gc.garbage`` 。使用 ``__del__``
   的对象可以通过 ``tp_finalize`` 机制安全回收。

通过示例脚本验证
----------------

运行 :file:`examples/gc_cycles_demo.py`：

.. code-block:: text

    --- 三色标记模拟 ---
    对象: A → B → C → A (循环)
    初始: refcount(A)=2, refcount(B)=2, refcount(C)=2
    减去外部引用后: gc_refs(A)=1, gc_refs(B)=1, gc_refs(C)=1
    → 被外部引用了，不可达? NO

    对象: X → Y → Z → Y (循环，X 无外部引用)
    初始: refcount(X)=1, refcount(Y)=2, refcount(Z)=1
    减去外部引用: gc_refs(X)=0, gc_refs(Y)=0, gc_refs(Z)=0
    → 都不可达！

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 三色标记是什么？
     - 白（不可达）→ 灰（待传播）→ 黑（可达）
   * - gc_refs 怎么算？
     - ob_refcnt - 来自堆外的引用数
   * - 循环引用怎么检测？
     - gc_refs 为 0 的对象就是环中的对象
   * - __del__ 对象怎么处理？
     - 移到 gc.garbage，由开发者处理
   * - GC 头在哪？
     - PyGC_Head 嵌入在 PyObject_HEAD 之前

参考资料
--------

- :ref:`gc-gc` — 分代 GC 总览
- :ref:`gc-arena` — 内存池与 arena 回收
- :file:`Python/gc.c` — ``deduce_unreachable`` 实现
- :file:`Include/internal/pycore_gc.h` — ``PyGC_Head`` 结构
- `三色标记算法 <https://en.wikipedia.org/wiki/Tracing_garbage_collection#Tri-color_marking>`__

