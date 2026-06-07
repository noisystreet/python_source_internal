内置类型 — set (PySetObject)
================================

``set`` 和 ``dict`` 共享同一个哈希表实现的核心逻辑，但只存键，不存值。

从一道题开始
------------

.. code-block:: python

    s = {3, 1, 4, 1, 5, 9}
    print(s)  # {1, 3, 4, 5, 9} — 不重复、无序

CPython 的 ``set`` 底层就是一张**哈希表**，和 ``dict`` 几乎一样——但每个条目只存键，不存值。

第一问：PySetObject 的结构
--------------------------

.. code-block:: c

    typedef struct {
        PyObject_HEAD
        Py_ssize_t used;          // 已用条目数
        Py_hash_t hash;           // 仅在 frozenset 中使用
        Py_ssize_t fill;          // 已填充总数（含 dummy）
        Py_ssize_t mask;          // 哈希表掩码（size - 1）
        PyObject **table;         // 哈希表指针数组
        PyObject *smalltable[8];  // 小集合的内嵌表（≤8 个元素）
        Py_ssize_t fingers;       // 遍历偏移量
    } PySetObject;

和 ``dict`` 的关键区别：

- ``smalltable``：元素 ≤ 8 时直接使用内嵌数组，不需要堆分配哈希表
- ``table`` 指向 ``smalltable``（小集合）或堆分配的表（大集合）
- ``fill`` 包括已用和已删除的"虚位"（dummy）条目

.. mermaid::

    flowchart LR
        subgraph SmallSet["小集合 (≤8个元素)"]
            smalltable["smalltable[8]<br/>内嵌数组"]
            table_ptr["table → smalltable"]
        end
        subgraph LargeSet["大集合 (>8个元素)"]
            heap_table["堆分配的哈希表"]
            table_ptr2["table → heap_table"]
        end

第二问：集合操作的字面量优化
----------------------------

.. code-block:: python

    # 这三个创建的集合不同：
    s1 = {1, 2, 3}          # 用 BUILD_SET 字节码
    s2 = set()              # 空集合，用 PySet_New
    s3 = set([1, 2, 3])     # 从列表创建

``{1, 2, 3}`` 在编译时被解析为 ``BUILD_SET`` 指令，执行时直接创建集合并填入元素。

第三问：frozenset
------------------

``frozenset`` 和 ``set`` 使用相同的 ``PySetObject`` 结构，区别在于：

- ``frozenset`` 创建后不允许修改（没有 ``add``、``remove`` 等方法）
- ``frozenset`` 的 ``ob_hash`` 会被缓存（set 不可哈希）
- ``frozenset`` 可以作为字典的键

在 C 层，``PyFrozenSet_Type`` 中没有 ``tp_setattro``，也没有 ``sq_ass_item``，
所以任何修改操作都会抛出 ``TypeError``。

通过示例脚本验证
----------------

运行 :file:`examples/tuple_set_demo.py` 中的 set 部分：

.. code-block:: text

    --- set 结构 ---
    小集合: 使用 smalltable
    大集合: 使用哈希表

    --- 集合运算 ---
    交集、并集、差集

    --- frozenset ---
    可哈希: True
    可变: False

小结
----

.. list-table::
   :header-rows: 1

   * - 特性
     - 实现方式
   * - 数据结构
     - 哈希表（类似 dict，只存键）
   * - 小集合优化
     - smalltable[8] 内嵌数组
   * - 集合运算
     - 交集/并集/差集用哈希表实现
   * - 哈希
     - 仅 frozenset 缓存哈希
