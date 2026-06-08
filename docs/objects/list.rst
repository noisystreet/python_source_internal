.. _objects-list:

内置类型 — list (PyListObject)
==================================

.. epigraph::

   "The programmer's chief tool is the ability to manage complexity."

   -- Bjarne Stroustrup


Python 的 ``list`` 是一个**动态数组**——它像 C 的数组一样支持 O(1) 随机访问，
但又可以自动扩容。

从一道题开始
------------

.. code-block:: python

    lst = []
    lst.append(1)  # 此时发生了什么？
    lst.append(2)  # 内存不够了怎么办？

list 的底层就是 **一个 C 指针数组 + 一个容量标记** 。

.. mermaid::

    flowchart LR
        subgraph PyListObject
            ob_size["ob_size = 3 （元素个数）"]
            allocated["allocated = 4 （容量）"]
            ob_item["ob_item → [ptr1, ptr2, ptr3, unused]"]
        end
        ob_item --> e1["PyObject 1"]
        ob_item --> e2["PyObject 2"]
        ob_item --> e3["PyObject 3"]

第一问：PyListObject 的结构
----------------------------

.. code-block:: c

    typedef struct {
        PyObject_VAR_HEAD          // PyObject_HEAD + ob_size
        PyObject **ob_item;        // 指向元素指针数组
        Py_ssize_t allocated;      // 已分配容量
    } PyListObject;

三个字段各司其职：

- ``ob_size`` （来自 ``PyObject_VAR_HEAD`` ）：当前元素个数，即 ``len(lst)``
- ``ob_item`` ：指向一个 ``PyObject*`` 数组的首地址
- ``allocated`` ：总共分配了多少空间（``ob_size <= allocated`` ）

当 ``ob_size == allocated`` 时，再添加元素就需要扩容。

第二问：append 的扩容策略
--------------------------

``list.append`` 使用**指数扩容**策略：

.. code-block:: c

    // listobject.c 中扩容的核心逻辑（简化）
    static int list_resize(PyListObject *self, Py_ssize_t new_size)
    {
        Py_ssize_t allocated = self->allocated;

        if (allocated >= new_size && new_size >= (allocated >> 1)) {
            // 容量够用或缩减不超过一半，直接更新 ob_size
            self->ob_size = new_size;
            return 0;
        }

        // 计算新容量
        Py_ssize_t new_allocated = (new_size >> 3) + (new_size < 9 ? 3 : 6);
        new_allocated += new_size;

        // 重新分配 ob_item 数组
        PyObject **items = PyMem_Realloc(self->ob_item,
                                         new_allocated * sizeof(PyObject*));
        self->ob_item = items;
        self->allocated = new_allocated;
        self->ob_size = new_size;
        return 0;
    }

.. mermaid::

    flowchart TD
        append["lst.append(x)"] --> check{"ob_size == allocated?"}
        check -->|"否, 有空位"| store["ob_item[ob_size] = x<br/>ob_size++"]
        check -->|"是, 满了"| resize["扩容<br/>new = (size>>3)+(size<9?3:6)+size"]
        resize --> store

这个扩容策略保证了 **连续的 append 操作平摊复杂度为 O(1)** （摊销分析）。
虽然单次扩容是 O(n)，但扩容次数很少。

第三问：insert 和 pop 的复杂度
-------------------------------

.. code-block:: python

    lst.insert(0, x)   # 所有元素后移 O(n)
    x = lst.pop(0)     # 所有元素前移 O(n)
    lst.pop()          # 最后一个元素，O(1)

在 C 层，``list.insert(0, x)`` 就是：

.. code-block:: c

    // listobject.c 中的 ins1 函数
    memmove(&items[where+1], &items[where],
            (self->ob_size - where) * sizeof(PyObject*));
    items[where] = x;
    self->ob_size++;

``memmove`` 是将索引 ``where`` 之后的元素全部往后挪一位。头部插入就是 O(n)。

``list.pop()`` （尾部弹出）则是 O(1)：

.. code-block:: c

    // listobject.c 中的 list_pop
    PyObject *v = items[self->ob_size - 1];
    self->ob_size--;
    return v;

而 ``list.pop(0)`` 需要 ``memmove`` 前移所有元素，也是 O(n)。

第四问：list 的迭代和修改
--------------------------

遍历 list 时不能修改它——因为 ``ob_item`` 和 ``ob_size`` 会变化：

.. code-block:: python

    lst = [1, 2, 3]
    for x in lst:
        lst.append(4)   # 无限循环！

在 C 层，list 的迭代器保存了对原始 ``ob_item`` 和 ``ob_size`` 的引用。
当你修改 list 时，迭代器持有的指针可能已经过时（扩容后 ``ob_item`` 指向了新地址）。

CPython 在 3.12+ 中会在某些情况下检测这种修改并抛出 ``RuntimeError`` 。

第五问：list.sort() 的实现
---------------------------

Python 的 ``list.sort()`` 使用 **Timsort** 算法——一种结合归并排序和插入排序的
混合算法，对现实世界的数据（部分有序）有很好的性能。

在 C 层，sort 临时将 ``allocated`` 设为 ``-1`` 来检测并发修改：

.. code-block:: c

    // list_sort 中
    self->allocated = -1;  // 标记正在排序
    // ... 执行排序 ...
    self->allocated = old_allocated;  // 恢复

这就是为什么在 sort 期间修改 list 会抛出异常。

通过示例脚本验证
----------------

运行 :file:`examples/list_demo.py`：

.. code-block:: text

    --- list 内部结构 ---
    空列表: ob_size=0, allocated=0, ob_item=None

    --- append 对容量的影响 ---
    append 1 个: len=1, allocated=4
    append 5 个: len=5, allocated=8
    append 9 个: len=9, allocated=16

    --- pop 对容量的影响 ---
    pop 到空: len=0, allocated=?（容量不缩减）

    --- insert(0) vs append ---
    insert(0): O(n) (memmove)
    append:    摊销 O(1)

小结
----

.. list-table::
   :header-rows: 1

   * - 特性
     - 实现方式
   * - 数据结构
     - 动态数组（PyObject* 指针数组）
   * - 扩容策略
     - 指数扩容（摊销 O(1)）
   * - 索引访问
     - O(1) — 直接读 ob_item[i]
   * - 尾部 append
     - 摊销 O(1)
   * - 头部 insert/pop
     - O(n) — memmove 移动元素
   * - 排序
     - Timsort

参考资料
--------

- :ref:`objects-pyobject` — PyVarObject 与变长对象
- :ref:`objects-iterators` — list 迭代器与序列协议
- :file:`Objects/listobject.c` — list 实现
