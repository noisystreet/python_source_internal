内存池与 Arena — 大块内存的管理
========================================

在 obmalloc 篇我们看到了 Arena/Pool/Block 三层结构。这一节深入
**Arena 的管理策略**——CPython 如何分配和释放大块内存。

从一道题开始
------------

obmalloc 的 Arena 是 1 MiB 的大块内存。问题是：**什么时候分配新的 Arena？
什么时候释放？**

CPython 的策略是：

- 需要新的 Pool 时，从当前 Arena 中切分
- 当前 Arena 用完了，分配一个新的 Arena（1 MiB）
- Arena 中所有 Pool 都空闲时，释放 Arena

第一问：Arena 的结构
---------------------

.. code-block:: c

    struct arena_object {
        uintptr_t address;           // Arena 基地址
        pymem_block *pool_address;   // 下一个可切分的 Pool 地址
        uint nfreepools;             // 空闲 Pool 数
        uint ntotalpools;            // 总 Pool 数
        struct pool_header *freepools; // 空闲 Pool 链表
        struct arena_object *nextarena;  // 链表
        struct arena_object *prevarena;
    };

``arena_object`` 本身是固定的——CPython 预分配了一个 ``arena_object`` 数组。
当需要新 Arena 时，从数组中取一个未使用的，调用 ``malloc`` 或 ``mmap`` 分配
实际的 1 MiB 内存。

.. mermaid::

    flowchart LR
        subgraph ArenaObjs["arena_objects[] (预分配数组)"]
            a0["arena 0<br/>address=0x..."]
            a1["arena 1<br/>address=0x..."]
            a2["arena 2<br/>未使用"]
            a3["arena 3<br/>未使用"]
        end
        a0 --> mem0["1 MiB 内存"]
        a1 --> mem1["1 MiB 内存"]

第二问：Arena 的分配策略
------------------------

当需要一个新 Pool 时：

.. code-block:: c

    // 从 arena 的 pool_address 处切分一个新 pool
    static poolp new_pool(void)
    {
        // 1. 从 usable_arenas 链表取一个有空闲 pool 的 arena
        arena_obj = usable_arenas;
        if (arena_obj == NULL) {
            // 2. 没有可用的 arena → 分配新 arena
            arena_obj = new_arena();
        }

        // 3. 从 arena 中切分一个 pool
        pool = (poolp)arena_obj->pool_address;
        arena_obj->pool_address += POOL_SIZE;
        arena_obj->nfreepools--;

        // 4. 初始化 pool
        pool->arenaindex = arena_obj - arenas;
        pool->szidx = DUMMY_SIZE_IDX;
        pool->freeblock = NULL;
        // ...

        return pool;
    }

``usable_arenas`` 是一个按 ``nfreepools`` 升序排列的双向链表。
当 Arena 中所有 Pool 都空闲时，它被从链表中移除并释放回系统。

第三问：mmap vs malloc
----------------------

CPython 使用 ``mmap`` 分配 Arena（如果平台支持），而不是 ``malloc``：

.. code-block:: c

    // 分配新 arena
    static struct arena_object *new_arena(void)
    {
        // 1. 取一个未使用的 arena_object
        arena_obj = unused_arena_objects;
        unused_arena_objects = arena_obj->nextarena;

        // 2. 分配 1 MiB 内存
    #ifdef HAVE_MMAP
        arena_obj->address = (uintptr_t)mmap(NULL, ARENA_SIZE,
                                              PROT_READ | PROT_WRITE,
                                              MAP_PRIVATE | MAP_ANONYMOUS,
                                              -1, 0);
    #else
        arena_obj->address = (uintptr_t)malloc(ARENA_SIZE);
    #endif

        // 3. 初始化
        arena_obj->pool_address = (pymem_block *)arena_obj->address;
        arena_obj->nfreepools = MAX_POOLS_IN_ARENA;
        arena_obj->ntotalpools = MAX_POOLS_IN_ARENA;
        // ...
    }

使用 ``mmap`` 的优势：

- 可以**单独释放**回系统（``malloc`` 的大块内存可能被 C 库缓存）
- 减少堆碎片（因为 mmap 区域独立于堆）
- 地址空间随机化 (ASLR)

第四问：Arena 的释放条件
------------------------

Arena 在**所有 Pool 都空闲**时才会被释放。一个 Pool 变空的时机：

- 释放 Pool 中最后一个 block 时，Pool 变空
- 空 Pool 被放回 Arena 的 ``freepools`` 链表
- 如果 Arena 中所有 Pool 都空了，该 Arena 被释放

.. code-block:: c

    // 释放 pool 时检查
    // 在 PyObject_Free 的释放路径中
    if (pool->ref.count == 0) {
        // Pool 空了
        // 移除 pool 的 size class 链表
        // 归还到 arena 的 freepools
        insert_to_freepool(arena, pool);

        // 检查 arena 是否全空
        if (--arena->nfreepools == arena->ntotalpools) {
            // Arena 全空 → 释放
            free_arena(arena);
        }
    }

第五问：Radix Tree 地址查找
----------------------------

当 ``PyObject_Free`` 收到一个地址时，它需要快速找到这个地址属于哪个 Pool。
CPython 使用 **Radix Tree（基数树）** 来做地址到 arena 的映射：

.. code-block:: c

    // 检查一个地址是否属于 obmalloc 管理
    static int address_in_range(void *p, poolp pool)
    {
        // 通过 radix tree 查找地址对应的 arena
        // 避免了维护一个巨大的页表
        return pymalloc_radix_tree_find(p) != NULL;
    }

.. mermaid::

    flowchart TD
        free["PyObject_Free(ptr)"] --> check{"ptr ≤ 512 B ?"}
        check -->|"否"| sys_free["系统 free(ptr)"]
        check -->|"是"| radix["Radix Tree 查找<br/>ptr → arena"]
        radix --> pool["找到 Pool<br/>归还 block"]
        pool --> pool_full{"Pool 空了?"}
        pool_full -->|"是"| arena_check{"Arena 全空?"}
        arena_check -->|"是"| free_arena["释放 Arena"]
        arena_check -->|"否"| done
        pool_full -->|"否"| done

通过示例脚本验证
----------------

运行 :file:`examples/arena_demo.py`：

.. code-block:: text

    --- Arena 容量 ---
    Arena 大小: 1 MiB (1048576 字节)
    每 Arena Pool 数: 64 (16 KiB 每个)
    Pool 大小: 16 KiB (16384 字节)

    --- mmap  vs  malloc ---
    平台支持 mmap: True
    Arena 通过 mmap 分配

    --- Arena 生命周期 ---
    分配第一个对象 → 分配 Arena 0
    分配更多对象 → 在 Arena 0 内切分 Pool
    Arena 0 用满 → 分配 Arena 1
    释放所有对象 → Arena 0 释放

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - Arena 多大？
     - 1 MiB（可配置）
   * - 每个 Arena 多少 Pool？
     - 64 个 (16 KiB 每个)
   * - Arena 怎么分配？
     - mmap (匿名映射) 或 malloc
   * - 什么时候释放 Arena？
     - 所有 Pool 都空闲时
   * - 地址怎么查找？
     - 通过 Radix Tree 快速定位
