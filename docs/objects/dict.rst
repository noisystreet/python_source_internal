内置类型 — dict (PyDictObject)
==================================

Python 的 ``dict`` 是语言的核心——它是对象的属性字典、全局/局部命名空间、
``__dict__``、以及 ``**kwargs`` 的底层实现。Python 程序运行时的每一步操作
几乎都在和字典打交道。

从一道题开始
------------

.. code-block:: python

    d = {"name": "Alice", "age": 30, "city": "Beijing"}

当你写 ``d["age"]`` 时，CPython 如何在 O(1) 时间内找到 ``30``？

答案是**哈希表**——Python 的 ``dict`` 本质上就是一张哈希表。但 CPython 的哈希表经过高度优化，
不是教科书中简单的"数组 + 链表"实现。

.. mermaid::

    flowchart TD
        lookup["d['age']"] --> hash["计算 'age' 的哈希值"]
        hash --> index["hash & mask → 索引"]
        index --> probe["线性探测解决冲突"]
        probe --> found["找到 entry → 返回值"]

第一问：PyDictObject 的结构
----------------------------

.. code-block:: c

    typedef struct {
        PyObject_HEAD
        Py_ssize_t ma_used;          // 字典中条目数
        uint64_t _ma_watcher_tag;    // 字典观察者标记
        PyDictKeysObject *ma_keys;   // 键表（哈希索引 + 键值对）
        PyDictValues *ma_values;     // 值数组（split table 模式）
    } PyDictObject;

字典有两种内部布局：

**组合表 (Combined Table)**：``ma_values == NULL``，键值对都存储在 ``ma_keys`` 中
**分离表 (Split Table)**：``ma_values != NULL``，键存储在 ``ma_keys``，值存在 ``ma_values`` 中

分离表主要用于**对象属性字典**（``object.__dict__``）——同一个类的所有实例共享同一份键表，
每个实例只存储自己的值数组，大幅节省内存。

第二问：键表的内部布局
----------------------

``PyDictKeysObject`` 是字典的"大脑"：

.. code-block:: c

    struct _dictkeysobject {
        Py_ssize_t dk_refcnt;         // 引用计数（分离表共享）
        uint8_t dk_log2_size;         // 哈希表大小的对数
        uint8_t dk_log2_index_bytes;  // 索引项字节数的对数
        uint8_t dk_kind;              // 键类型
        uint32_t dk_version;          // 版本号
        Py_ssize_t dk_usable;         // 可用条目数
        Py_ssize_t dk_nentries;       // 已用条目数

        char dk_indices[];   // 变长：哈希索引数组（1/2/4/8 字节每项）
        // 后面跟着 dk_entries[]：键值对数组
    };

内存布局是这样的：

.. code-block:: text

    dk_indices[]          dk_entries[]
    ┌─────┐              ┌──────────────┐
    │  3  │              │  "name"      │
    ├─────┤              │  "Alice"     │
    │  -1 │ <- 空        ├──────────────┤
    ├─────┤              │  "age"       │
    │  0  │              │  30          │
    ├─────┤              ├──────────────┤
    │  -1 │ <- 空        │  "city"      │
    ├─────┤              │  "Beijing"   │
    │  1  │              └──────────────┘
    └─────┘

查找过程：

#. 计算 ``hash(key)``
#. ``index = hash & (size - 1)``（取模）
#. 读 ``dk_indices[index]``，得到 entry 索引
#. 如果是 ``-1``（``DKIX_EMPTY``），键不存在
#. 比较 ``dk_entries[entry].key`` 是否等于目标键

索引数组的每个元素大小根据哈希表大小自动选择：小表用 1 字节，大表用 2/4/8 字节。

第三问：哈希冲突怎么解决？
--------------------------

CPython 使用**线性探测 (Linear Probing)**：

.. code-block:: c

    // dictobject.c 中的查找逻辑（简化）
    Py_ssize_t _Py_dict_lookup(PyDictObject *mp, PyObject *key, ...)
    {
        PyDictKeysObject *dk = mp->ma_keys;
        Py_hash_t hash = PyObject_Hash(key);
        // 取模得到初始索引
        size_t i = hash & (DK_SIZE(dk) - 1);

        while (DK_ENTRIES(dk)[i].key != key) {
            if (DK_ENTRIES(dk)[i].key == NULL) {
                return DKIX_EMPTY;  // 没找到
            }
            // 线性探测：i = (i + 1) & mask
            i = (i + 1) & (DK_SIZE(dk) - 1);
        }
        return i;
    }

当两个不同的 key 映射到同一个索引时，CPython 简单地**往前走一格**。如果那一格也被占了，
继续往前走，直到找到空位或找到目标键。

.. note::

   线性探测的平均查找长度取决于**负载因子 (Load Factor)**。CPython 的字典负载因子约为 **2/3**
   （``USABLE_FRACTION``），即在哈希表满 2/3 之前不会扩容。这保证了 O(1) 的平均查找复杂度。

当字典大小超过负载因子限制时，CPython 会**扩容**：

- 新大小为原大小的 2 倍
- 重新计算所有哈希值在新表中的位置
- 释放旧表

第四问：分离表 (Split Table) 优化
----------------------------------

当你写 ``obj.attr = value`` 时，Python 将 ``attr`` 存在 ``obj.__dict__`` 中。
如果每个对象都拥有一份完整的键表，内存开销会很大。

分离表解决了这个问题：

.. mermaid::

    flowchart LR
        subgraph Class["类对象"]
            keys["共享键表<br/>ma_keys (所有实例共用)"]
        end
        subgraph Instance1["实例1"]
            v1["ma_values<br/>[val1, val2, ...]"]
        end
        subgraph Instance2["实例2"]
            v2["ma_values<br/>[val1, val2, ...]"]
        end
        Instance1 --> keys
        Instance2 --> keys

同一个类创建的实例共享相同的 ``ma_keys``（因为属性名相同），但每个实例有自己的
``ma_values`` 数组。当 ``obj.attr`` 被访问时，CPython 通过属性名在共享键表中找到索引，
然后从自己的 ``ma_values`` 中取值。

这个优化在 PEP 412 中引入，能节省大约 **30%-50%** 的对象属性字典内存。

第五问：字典的版本号 (dk_version)
----------------------------------

``PyDictKeysObject`` 中的 ``dk_version`` 是一个递增的计数器。每次对字典的修改
都会重置它为 0（或递增）。

这个版本号被 **Tier 2 优化器** 和 **字典观察者 (watchers)** 使用：

.. code-block:: c

    // 字典观察者注册
    PyDict_AddWatcher(callback);
    PyDict_Watch(watcher_id, dict);

    // 当 dict 被修改时，callback 被自动调用

这个机制被用于：

- **PEP 669 监控系统**：追踪字典修改
- **类型属性缓存**：当类型字典被修改时，自动使相关字节码失效
- **帧变量缓存**：优化局部变量的访问

第六问：为什么 Python 3.7+ 的 dict 保持插入顺序？
--------------------------------------------------

自 Python 3.7 起，``dict`` 保证**插入顺序**。这个特性源于 PEP 468。

在 C 层，虽然 ``dk_entries`` 是哈希表，但迭代器按 **``dk_entries`` 数组的插入顺序**遍历，
而不是按哈希索引顺序。因为 ``dk_nentries`` 是递增的，新条目总是追加到 ``dk_entries`` 末尾。

.. code-block:: c

    // PyDict_Next 遍历顺序
    // pos 从 0 递增到 dk_nentries - 1
    // 这个顺序就是插入顺序

这也是为什么 ``**kwargs`` 在 Python 3.7+ 中保持参数传入顺序。

通过示例脚本验证
----------------

运行 :file:`examples/dict_demo.py`：

.. code-block:: text

    --- 字典基础操作 ---
    d['age'] = 30

    --- 哈希表查找 ---
    查找 'age' 的索引...

    --- 扩容 ---
    初始容量: 8
    插入第 6 个键后: 扩容到 16

    --- 分离表 vs 组合表 ---
    实例属性字典: split table（共享键表）
    普通字典: combined table

    --- 版本号变化 ---
    添加键: version 重置
    删除键: version 重置

小结
----

.. list-table::
   :header-rows: 1

   * - 特性
     - 实现方式
   * - 数据结构
     - 哈希表（线性探测）
   * - 索引数组
     - dk_indices[] 变长，1/2/4/8 字节/项
   * - 负载因子
     - ~2/3，超限后 2 倍扩容
   * - 属性 __dict__ 优化
     - 分离表 (split table)，共享键
   * - 插入顺序保持
     - dk_entries 按追加顺序排列
   * - 版本号
     - dk_version，用于监控和缓存失效
