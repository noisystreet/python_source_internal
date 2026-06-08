.. _gc-obmalloc:

小块内存分配器 (obmalloc) — Python 的 malloc
====================================================

.. epigraph::

   "The limits of my language mean the limits of my world."

   -- Ludwig Wittgenstein


CPython 在系统 ``malloc`` 之上实现了一个**专用的小块内存分配器** （obmalloc），
专门为频繁创建和销毁的小对象（≤512 字节）设计。

从一道题开始
------------

.. code-block:: python

    a = 42
    b = [1, 2, 3]
    c = "hello"

这三个对象的创建，在内存分配上有何不同？

- ``a = 42`` ：来自小整数池，根本不走内存分配器
- ``b = [1, 2, 3]`` ：列表本身走 ``PyObject_New`` → obmalloc
- ``c = "hello"`` ：紧凑字符串，``PyUnicodeObject`` + 字符数据走 obmalloc

大部分 Python 对象都小于 512 字节，它们都通过 obmalloc 分配。

.. mermaid::

    flowchart TD
        alloc["PyObject_Malloc(size)"] --> check{"size ≤ 512?"}
        check -->|"是"| obmalloc["obmalloc 分配<br/>从 pool 中取一块"]
        check -->|"否"| sys_malloc["系统 malloc<br/>(或 mimalloc)"]
        obmalloc --> result["返回地址"]
        sys_malloc --> result

第一问：obmalloc 为什么存在？
-----------------------------

CPython 不用系统 ``malloc`` 直接分配小对象的原因：

1. **系统 malloc 的开销** ：每个 ``malloc(24)`` 可能消耗 32-48 字节的元数据
2. **内存碎片** ：大量小对象的分配和释放会产生碎片
3. **性能** ：obmalloc 对小对象可以做到 O(1) 分配和释放

obmalloc 的设计目标是：**对 ≤512 字节的请求，提供接近自由列表的速度，
同时保持可接受的内存使用率**。

第二问：三层结构 — Arena / Pool / Block
----------------------------------------

obmalloc 管理内存的三级层次：

.. code-block:: text

    Arena（竞技场）— 1 MiB
      └── Pool（池）— 16 KiB (大池) 或 4 KiB (标准池)
            └── Block（块）— 8B, 16B, 24B, ..., 512B

**Arena** （1 MiB）
  从系统一次性分配的大块内存。每个 arena_object 记录其状态。

**Pool** （16 KiB / 4 KiB）
  Arena 被划分为多个 pool。每个 pool 只服务一种**大小类 (size class)** 。

**Block** （8~512 字节）
  每次 ``PyObject_Malloc`` 返回的块。大小按 16 字节（64 位）向上取整。

.. mermaid::

    graph TD
        subgraph Arena["Arena (1 MiB)"]
            pool1["Pool 0<br/>16 KiB<br/>size class: 0 (8B)"]
            pool2["Pool 1<br/>16 KiB<br/>size class: 1 (16B)"]
            pool3["Pool 2<br/>16 KiB<br/>size class: 1 (16B)"]
            poolN["...更多 pools"]
        end
        subgraph Pool["Pool (16 KiB) 内部"]
            header["pool_header<br/>(元数据)"]
            b1["block 0 (16B)"]
            b2["block 1 (16B)"]
            bn["...更多 blocks"]
        end
        pool1 --> header

第三问：大小类 (Size Class)
---------------------------

请求大小被向上取整到 16 的倍数（64 位），对应一个大小类索引：

.. code-block:: text

    请求字节数       实际分配     大小类索引
    ─────────────────────────────────────
      1-16            16           0
     17-32            32           1
     33-48            48           2
     ...              ...
    497-512          512          31

定义在源码中：

.. code-block:: c

    #define ALIGNMENT           16          // 64 位系统
    #define ALIGNMENT_SHIFT      4
    #define SMALL_REQUEST_THRESHOLD 512
    #define NB_SMALL_SIZE_CLASSES (512 / 16)  // 32 类

    // 从索引计算大小
    #define INDEX2SIZE(I) (((pymem_uint)(I) + 1) << ALIGNMENT_SHIFT)

``usedpools`` 数组维护了每个大小类中**部分使用的 pool** 的双向链表：

.. code-block:: c

    // usedpools[2*i] — 大小类 i 的部分使用 pool 链表头
    // 分配时从表头取一个 pool，从它的 freeblock 取一块
    // 释放时把块归还到 pool 的 freeblock

第四问：Pool 的内部结构
-----------------------

每个 pool 包含一个头部和若干相同大小的 block：

.. code-block:: c

    struct pool_header {
        union { pymem_block *_padding;
                uint count; } ref;     // 已分配的 block 数
        pymem_block *freeblock;        // ★ 空闲块链表头
        struct pool_header *nextpool;  // 链表前驱/后继
        struct pool_header *prevpool;
        uint arenaindex;               // 所属 arena 索引
        uint szidx;                    // 大小类索引
        uint nextoffset;               // 下一个未使用块的偏移
        uint maxnextoffset;            // 最大有效偏移
    };

``freeblock`` 是核心——它是一个**单向空闲链表** 。分配时：

.. code-block:: c

    // 从 pool 分配一个块（简化）
    void *p = (void *)pool->freeblock;
    if (p != NULL) {
        pool->freeblock = *(pymem_block **)p;  // freeblock 指向链表下一个
        pool->ref.count++;
        return p;
    }
    // 如果 freeblock 用完了，从 nextoffset 处取新的块
    if (pool->nextoffset <= pool->maxnextoffset) {
        p = (pymem_block *)pool + pool->nextoffset;
        pool->nextoffset += INDEX2SIZE(pool->szidx);
        pool->ref.count++;
        return p;
    }
    // pool 满了

.. mermaid::

    flowchart LR
        subgraph Pool_Free["Pool.freeblock"]
            head["→ block 3"]
        end
        block3["block 3"] --> block7["block 7"]
        block7 --> block12["block 12"]
        block12 --> null["NULL"]
        Pool_Free --> block3

释放时，把块插回 ``freeblock`` 链表头部：

.. code-block:: c

    // 释放一个块（简化）
    *(pymem_block **)p = pool->freeblock;  // 指向原链表头
    pool->freeblock = p;                    // 成为新的链表头
    pool->ref.count--;

第五问：Pool 的生命周期
-----------------------

Pool 有三种状态：

.. list-table::
   :header-rows: 1

   * - 状态
     - 所在链表
     - 含义
   * - 已用完 (full)
     - 不在任何链表
     - 所有 block 都已分配
   * - 部分使用 (used)
     - ``usedpools[szidx]``
     - 还有可用 block
   * - 空闲 (empty)
     - ``arena.freepools``
     - 所有 block 都已释放，可回收

分配流程：

#. 从 ``usedpools[szidx]`` 取一个部分使用的 pool
#. 从 pool 的 ``freeblock`` 取一个块
#. 如果 pool 满了，从链表中移除

释放流程：

#. 找到块所属的 pool（通过地址位运算）
#. 把块归还到 pool 的 ``freeblock``
#. 如果 pool 从满变部分使用，插回 ``usedpools``
#. 如果 pool 变空，放回 arena 的 ``freepools``

第六问：Arena 管理
------------------

当需要新的 pool 时，obmalloc 从 arena 中切分：

.. code-block:: c

    struct arena_object {
        uintptr_t address;           // arena 基地址
        pymem_block *pool_address;   // 下一个可用的 pool 地址
        uint nfreepools;             // 空闲 pool 数
        uint ntotalpools;            // 总 pool 数
        struct pool_header *freepools; // 空闲 pool 链表
    };

当 arena 中所有 pool 都空闲时，arena 被释放回系统。

通过示例脚本验证
----------------

运行 :file:`examples/obmalloc_demo.py`：

.. code-block:: text

    --- 大小类映射 ---
    malloc(10)  → 16 字节 (class 0)
    malloc(30)  → 32 字节 (class 1)
    malloc(100) → 112 字节 (class 6)
    malloc(500) → 512 字节 (class 31)
    malloc(600) → 走系统 malloc

    --- pool 内部 ---
    每个 16 KiB pool:
      大小类 0 (16B): 约 1023 个 block
      大小类 31 (512B): 约 31 个 block

    --- 分配性能 ---
    obmalloc:  ~50ns/次
    系统 malloc: ~150ns/次

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - obmalloc 管什么？
     - ≤512 字节的小对象分配
   * - 三层结构？
     - Arena (1 MiB) → Pool (16 KiB) → Block (8-512B)
   * - 怎么避免碎片？
     - 每个 pool 只服务一种大小类
   * - 分配和释放多快？
     - O(1)，仅修改链表指针
   * - Pool 用完怎么办？
     - 从 arena 切分新 pool
   * - Arena 什么释放？
     - 所有 pool 都空时释放

参考资料
--------

- :ref:`gc-arena` — arena 是 pymalloc 的上层结构
- :ref:`extensions-memory-api` — C API 中的内存分配接口
- :file:`Objects/obmalloc.c` — pymalloc 实现
