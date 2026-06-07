__slots__ 的底层实现
============================

``__slots__`` 是 Python 中用于**限制实例属性**并**节省内存**的机制。
这一节从 C 层的角度解释它的工作原理。

从一道题开始
------------

.. code-block:: python

    class WithSlots:
        __slots__ = ("x", "y")

    obj = WithSlots()
    obj.x = 10   # 正常
    obj.z = 20   # AttributeError: 'WithSlots' object has no attribute 'z'

为什么 ``obj.z`` 会报错？为什么 ``WithSlots`` 的实例比普通类更省内存？

第一问：__slots__ 的核心原理
----------------------------

在 C 层，``__slots__`` 做的事情很简单：**禁止创建** ``__dict__`` **字典**，并**为每个 slot 名在类型的** ``tp_members`` **中创建对应的** ``PyMemberDef``。

.. code-block:: c

    // 当 Python 解析 class 定义遇到 __slots__ 时：
    // 1. 从类字典中移除 __slots__ 条目
    // 2. 为每个 slot 名创建一个 PyMemberDef（类型为 T_OBJECT_EX）
    // 3. 将 tp_dictoffset 设为 0（禁止 __dict__）
    // 4. 调整 tp_basicsize 为每个 slot 留出指针空间

.. mermaid::

    flowchart LR
        subgraph Normal["普通类实例"]
            header["PyObject_HEAD<br/>16B"]
            dict_ptr["__dict__ 指针<br/>8B"]
            weakref["__weakref__ 指针<br/>8B"]
        end
        subgraph Slots["__slots__ 类实例"]
            header2["PyObject_HEAD<br/>16B"]
            x_slot["x (PyObject*)<br/>8B"]
            y_slot["y (PyObject*)<br/>8B"]
        end

第二问：tp_basicsize 的调整
----------------------------

CPython 在创建类时，根据 ``__slots__`` 调整类型的 ``tp_basicsize`` ：

.. code-block:: c

    // Objects/typeobject.c 中的逻辑（简化）
    static PyObject *slot_tp_new(PyTypeObject *type, ...)
    {
        // 计算 slots 所需的总大小
        Py_ssize_t slots_size = 0;
        for (each slot name in __slots__) {
            slots_size += sizeof(PyObject *);
        }

        // tp_basicsize = 基础大小 + slots 空间
        type->tp_basicsize = sizeof(PyObject) + slots_size;

        // 如果没定义 __dict__，设置 tp_dictoffset = 0
        if (!has_dict) {
            type->tp_dictoffset = 0;
        }
    }

第三问：slot 的访问路径
-----------------------

普通属性的访问路径是：**实例 → __dict__ 字典 → 哈希查找**

``__slots__`` 属性的访问路径是：**实例 → 偏移量指针 → 直接取值**

.. code-block:: c

    // slot 属性读取（通过 PyMember_GetOne）
    PyObject *PyMember_GetOne(const char *addr, PyMemberDef *member)
    {
        // addr + member->offset 就是 slot 值所在的位置
        PyObject *result = *(PyObject **)(addr + member->offset);
        if (result == NULL) {
            // slot 未设置 → AttributeError
            PyErr_SetString(PyExc_AttributeError, member->name);
            return NULL;
        }
        return result;
    }

没有字典查找的开销，这就是 ``__slots__`` 比 ``__dict__`` 存取更快的原因。

第四问：多继承与 __slots__
--------------------------

多继承时，``__slots__`` 需要显式指定每个父类的 slot：

.. code-block:: python

    class A:
        __slots__ = ("x",)

    class B(A):
        __slots__ = ("y",)  # 正确

    class C(A):
        pass                 # 正确，C 会有 __dict__

如果子类没有定义 ``__slots__``，它会自动获得 ``__dict__`` 。

通过示例脚本验证
----------------

运行 :file:`examples/slots_demo.py`：

.. code-block:: text

    --- 内存对比 ---
    普通类实例: 56 字节
    __slots__ 实例: 32 字节（节省 43%）

    --- 访问速度 ---
    普通类: 0.12s (1000 万次)
    __slots__: 0.08s (快 33%)

    --- 限制验证 ---
    实例未定义的 slot → AttributeError

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - __slots__ 省在哪？
     - 没有 __dict__ 字典，属性直接存在实例的固定偏移中
   * - 访问怎么变快的？
     - 指针偏移直接存取，免去哈希查找
   * - tp_dictoffset 设为 0 什么意思？
     - 告诉 CPython 这个类型的实例没有 __dict__
   * - 多继承要注意什么？
     - 子类也需定义 __slots__，否则父类的 slot 可能被覆盖
