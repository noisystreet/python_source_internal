.. _gc-gc:

分代垃圾回收 — 解决循环引用
=================================

.. epigraph::

   "What is recycled lives again."

   -- Seneca, Epistulae Morales ad Lucilium


引用计数可以处理大部分内存管理，但它有一个根本缺陷： **无法处理循环引用** 。
分代垃圾回收器 (GC) 就是为此而生。

从一道题开始
------------

.. code-block:: python

    class Node:
        def __init__(self):
            self.next = None

    a = Node()
    b = Node()
    a.next = b
    b.next = a   # 形成循环引用
    del a
    del b        # 引用计数 = 1（彼此指向），不触发回收

GC 的目标就是找到这种 **互相引用但外部已无引用的对象组** ，并把它们回收。

.. mermaid::

    flowchart TD
        subgraph Root["GC Roots (全局引用、栈引用)"]
            reachable1["可达对象 A"]
            reachable2["可达对象 B"]
        end
        subgraph Cycle["循环引用组 (不可达)"]
            c1["C → D → C"]
            c2["E → F → G → E"]
        end
        reachable1 --> reachable2
        c1 ~~~ c2

第一问：分代假设与三代结构
---------------------------

GC 基于 **分代假设** ：大多数对象存活时间很短，存活越久的对象越不可能死。

CPython 将对象分为三代：

.. list-table::
   :header-rows: 1

   * - 代
     - 名称
     - 收集阈值 (threshold)
     - 含义
   * - 0
     - 年轻代 (Young)
     - 700
     - 新创建的对象
   * - 1
     - 中年代 (Middle)
     - 10
     - 熬过一次 GC 的对象
   * - 2
     - 老年代 (Old)
     - 10
     - 熬过两次 GC 的对象

.. code-block:: c

    // pycore_gc.h
    #define NUM_GENERATIONS 3

    struct gc_generation {
        PyGC_Head head;        // 该代的双向链表头
        int threshold;         // 收集阈值
        int count;             // 当前计数器
    };

每创建一个 **容器对象** （可参与循环引用的对象），CPython 会：

#. 将其加入第 0 代链表
#. ``generations[0].count++``
#. 如果 ``count >= threshold`` ，触发第 0 代收集

第二问：GC 的触发时机
-----------------------

GC 在以下时机被触发：

**自动触发**
  当分配的可收集对象达到阈值时，在 ``PyObject_GC_Alloc`` 中：

  .. code-block:: c

      // gcmodule.c 中的分配钩子
      PyObject *PyObject_GC_Alloc(PyTypeObject *tp, ...)
      {
          // ...
          if (gcstate->generations[0].count > gcstate->generations[0].threshold) {
              _PyGC_Collect(tstate, GENERATION_AUTO, _Py_GC_REASON_HEAP);
          }
          // ...
      }

  ``GENERATION_AUTO`` 会让 GC 自动选择需要收集的最老代。

**手动触发**
  ``gc.collect()`` 或 ``gc.collect(generation)`` ：

  .. code-block:: python

      import gc
      gc.collect()      # 全代收集
      gc.collect(0)     # 只收集第 0 代

**阈值检查**
  ``gc.get_threshold()`` / ``gc.set_threshold()`` 可以查看和调整。

第三问：GC 的三步收集算法
--------------------------

``gc_collect_main`` 实现分代收集，核心分三步：

.. mermaid::

    flowchart TD
        start["gc_collect_main(generation)"] --> merge["1. 合并
        将年轻代对象移到当前代"]
        merge --> mark["2. 标记-清除
        deduce_unreachable()"]
        mark --> weakref["3. 处理弱引用和 finalizer"]
        weakref --> free["4. 释放不可达对象"]
        free --> done["更新计数器，返回回收数"]

**第 1 步：合并**
  将要收集的代及所有更年轻的代合并到当前代：

  .. code-block:: c

      // 将 0..generation-1 代的对象合并到 generation 代
      for (i = 0; i < generation; i++) {
          gc_list_merge(GEN_HEAD(gcstate, i), GEN_HEAD(gcstate, generation));
      }

**第 2 步：标记-清除 (``deduce_unreachable``)**
  核心函数，使用 **三色标记** 算法：

  .. code-block:: c

      static void deduce_unreachable(PyGC_Head *young, PyGC_Head *unreachable)
      {
          // 1. 将所有对象标记为"待定"
          // 2. 从 GC roots 出发，遍历可达对象，标记为"可达"
          // 3. 剩余的"待定"对象就是不可达的
          // 4. 将不可达对象移到 unreachable 链表
      }

  三色标记：

  .. list-table::
     :header-rows: 1

     * - 颜色
       - 含义
       - 在 GC 中的表示
     * - 白色
       - 未被访问
       - 在 ``unreachable`` 链表中
     * - 灰色
       - 自身已访问，但引用的对象未访问完
       - 临时标记
     * - 黑色
       - 已访问完毕
       - 留在 ``young`` （即"可达"）

  CPython 的实现使用 ``gc_refs`` 字段（存储在 PyGC_Head 中）作为标记位，
  通过 **可达性传播** 算法——从根对象出发，沿着引用链把所有可达对象标记出来。

**第 3 步：处理弱引用和 finalizer**
  调用 ``handle_weakrefs`` 清理指向不可达对象的弱引用，
  调用 ``finalize_garbage`` 执行 ``tp_finalize`` 。

**第 4 步：释放**
  遍历 ``unreachable`` 链表，对每个对象调用 ``tp_dealloc`` 。

第四问：GC 跟踪的对象
----------------------

不是所有对象都被 GC 跟踪。只有 **容器对象**——可以被弱引用或可能形成循环的对象。

``PyObject_GC_New`` 和 ``PyObject_GC_NewVar`` 创建的对象会被 GC 跟踪。

.. code-block:: c

    // 创建并跟踪
    PyObject *PyObject_GC_New(PyTypeObject *tp)
    {
        PyObject *op = PyObject_Malloc(_PyObject_SIZE(tp));
        op = _PyObject_GC_Init(op, tp);
        return op;
    }

    void _PyObject_GC_Init(PyObject *op, PyTypeObject *tp)
    {
        // 将对象加入第 0 代链表
        _PyGCHead_SET_REFS(gc, GC_REFS_REACHABLE);
        gc_list_append(gc, GEN_HEAD(gcstate, 0));
        gcstate->generations[0].count++;
    }

``gc.is_tracked(obj)`` 可以检查一个对象是否被 GC 跟踪。

第五问：GC 的调试工具
----------------------

CPython 的 GC 提供了丰富的调试支持：

.. code-block:: python

    import gc
    gc.set_debug(gc.DEBUG_STATS | gc.DEBUG_SAVEALL)

- ``DEBUG_STATS`` ：打印每次收集的统计信息
- ``DEBUG_SAVEALL`` ：将不可达对象保存到 ``gc.garbage`` 中（不释放）
- ``DEBUG_LEAK`` ：组合标志，用于调试内存泄漏
- ``gc.get_objects()`` ：返回所有被 GC 跟踪的对象
- ``gc.get_referrers(obj)`` ：返回引用 ``obj`` 的所有对象
- ``gc.get_referents(obj)`` ：返回 ``obj`` 引用的所有对象

通过示例脚本验证
----------------

运行 :file:`examples/gc_demo.py`：

.. code-block:: text

    --- 循环引用检测 ---
    创建循环引用
    gc.collect() 回收了 2 个对象

    --- 代际提升 ---
    第 0 代: 7 个对象
    第 1 代: 3 个对象
    第 2 代: 2 个对象

    --- __del__ 与 GC ---
    有 __del__ 的循环引用对象：不可回收
    gc.garbage 中可以看到它们

    --- gc.get_referrers ---
    obj 被 x, lst 引用

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - GC 解决了什么问题？
     - 引用计数无法处理的循环引用
   * - 分几代？
     - 3 代，阈值 700/10/10
   * - 什么触发 GC？
     - 第 0 代对象数超过阈值
   * - 用什么算法？
     - 三色标记的变种（deduce_unreachable）
   * - 哪些对象被跟踪？
     - 容器对象（PyObject_GC_New 创建的）
   * - 怎么调试？
     - gc.set_debug()、gc.get_objects()、gc.get_referrers()

参考资料
--------

- :ref:`objects-refcount` — 引用计数：GC 的前置基础
- :ref:`gc-cycles` — 循环引用检测算法细节
- :ref:`gc-arena` — arena 与内存池架构
- :pep:`442` — 安全终结的行为模型
- :file:`Python/gc.c` — GC 收集器实现
- :file:`Include/internal/pycore_gc.h` — GC 内部结构
- `Uniprocessor Garbage Collection Techniques <https://www.cs.utah.edu/~mflatt/papers/iwmm92.pdf>`__ — 分代 GC 基础论文

