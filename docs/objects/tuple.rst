内置类型 — tuple (PyTupleObject)
====================================

``tuple`` 和 ``list`` 看起来很像——都存着 ``PyObject*`` 数组。
但有一个关键区别：**tuple 是不可变的** 。

从一道题开始
------------

.. code-block:: python

    t = (1, 2, 3)
    # t[0] = 99  # TypeError!

    d = {t: "tuple as key"}  # 可以！tuple 可以哈希

tuple 不可变的特性带来两个重要后果：

#. **可哈希** ：tuple 可以作为字典的键
#. **内存更紧凑** ：不需要预留扩容空间

第一问：PyTupleObject 的结构
----------------------------

.. code-block:: c

    typedef struct {
        PyObject_VAR_HEAD           // 头部 + ob_size
        Py_hash_t ob_hash;          // 哈希值缓存（-1 表示未计算）
        PyObject *ob_item[1];       // 变长：元素指针数组
    } PyTupleObject;

和 ``PyListObject`` 相比，tuple 有两个关键差异：

- **没有 ``allocated`` 字段**——tuple 的大小在创建时就固定了
- **有 ``ob_hash`` 字段**——list 不能哈希，所以不需要缓存哈希值

因为不可变，``ob_size`` 就是最终大小。``ob_item`` 数组紧跟在结构体后面（和字符串类似的紧凑布局），
而不是通过指针指向堆上的另一块内存。

.. mermaid::

    graph LR
        subgraph PyTupleObject["PyTupleObject (紧凑)"]
            ob_size["ob_size = 4"]
            ob_hash["ob_hash = 0x..."]
            items["ob_item[0..3]"]
        end
        items --> e1["PyObject 1"]
        items --> e2["PyObject 2"]

第二问：tuple 的哈希值缓存
--------------------------

``ob_hash`` 字段在创建时设为 ``-1`` （未计算）。第一次调用 ``hash(t)`` 时：

.. code-block:: c

    static Py_hash_t tuplehash(PyObject *v)
    {
        PyTupleObject *t = (PyTupleObject *)v;
        if (t->ob_hash != -1) {
            return t->ob_hash;  // 已缓存
        }
        // 计算：组合每个元素的哈希值
        Py_hash_t hash = 0x345678;
        for (Py_ssize_t i = 0; i < Py_SIZE(t); i++) {
            hash ^= PyObject_Hash(t->ob_item[i]);
        }
        // 缓存结果
        t->ob_hash = hash;
        return hash;
    }

因为 tuple 不可变，所以哈希值**只计算一次，永久缓存** 。

第三问：单元素元组的陷阱
------------------------

.. code-block:: python

    >>> t = (42)     # 这是整数，不是元组！
    >>> type(t)
    <class 'int'>
    >>> t = (42,)    # 逗号才是元组的标志
    >>> type(t)
    <class 'tuple'>

在 C 层，创建长度为 1 的元组时也有一个特殊优化——**长度为 0 的元组是单例** ：

.. code-block:: c

    PyObject *PyTuple_New(Py_ssize_t size)
    {
        if (size == 0) {
            return Py_NewRef(&_Py_SINGLETON(tuple_empty));
        }
        // 分配内存：结构体 + size 个指针
        op = PyObject_GC_NewVar(PyTupleObject, &PyTuple_Type, size);
        op->ob_hash = -1;
        for (i = 0; i < size; i++) {
            op->ob_item[i] = NULL;
        }
        return op;
    }

空元组 ``()`` 是一个全局单例，永远不会被销毁。

第四问：tuple 和 list 的内存对比
--------------------------------

.. code-block:: text

    list:  结构体(24B) + ob_item指针(8B) + 元素数组(8B×n) + 预留空间
    tuple: 结构体(24B) + hash(8B) + 元素数组(8B×n)

tuple 比 list 少了 ``allocated`` 字段和额外的指针间接层，所以：

- 创建速度更快（一次分配，不需要预留额外空间）
- 访问速度略快（少一次指针解引用）
- 内存占用更少

通过示例脚本验证
----------------

运行 :file:`examples/tuple_set_demo.py` 中的 tuple 部分：

.. code-block:: text

    --- tuple 结构 ---
    空元组是单例: True
    tuple 哈希缓存: 第一次计算，之后缓存

    --- tuple vs list 内存 ---
    tuple(1000): 约 8KB
    list(1000):  约 16KB（含预留空间）

小结
----

.. list-table::
   :header-rows: 1

   * - 特性
     - 实现方式
   * - 数据结构
     - 定长数组（PyObject*[]）
   * - 哈希
     - 缓存于 ob_hash，只计算一次
   * - 空元组
     - 全局单例
   * - 可变性
     - 不可变 → 无扩容，可哈希
   * - 内存
     - 紧凑：元素数组嵌入结构体
