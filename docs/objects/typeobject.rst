PyTypeObject —— "类型"本身也是一个对象
=========================================

上一节我们知道了每个 Python 对象的头部都有一个 ``ob_type`` 指针：

.. code-block:: c

    struct _object {
        ...
        PyTypeObject *ob_type;  // 指向我是什么类型
    };

它指向的地方——``PyTypeObject``——是一个比 ``PyObject`` 复杂得多的结构体。
这一节，我们就来拆开它。

从一道题开始
------------

你在 Python 里写过这样的代码吧：

.. code-block:: python

    >>> type(42)
    <class 'int'>
    >>> type(type(42))
    <class 'type'>

第一个 ``type(42)`` 返回 ``int`` 类型——这个好理解。

但第二行：**``type`` 本身的类型也是 ``type``** 。这就像说"上帝创造了上帝自己"。

在 CPython 里，这句话的 C 层真相是：

.. code-block:: c

    PyLong_Type.ob_type == &PyType_Type  // int 的类型是 type
    PyType_Type.ob_type == &PyType_Type  // type 的类型也是 type

**类型本身也是一个对象。** ``PyTypeObject`` 就是一个描述"类型"的结构体，
而 ``PyType_Type`` （也就是 Python 里的 ``type`` ）是它的"类型"——一个指向自己的循环。

.. mermaid::

    flowchart TD
        obj42["42 (整数对象)"] -->|"ob_type"| PyLong_Type["PyLong_Type<br/>= int"]
        PyLong_Type -->|"ob_type"| PyType_Type["PyType_Type<br/>= type"]
        PyType_Type -->|"ob_type"| PyType_Type
        PyUnicode_Type["PyUnicode_Type<br/>= str"] -->|"ob_type"| PyType_Type
        PyList_Type["PyList_Type<br/>= list"] -->|"ob_type"| PyType_Type

第一问：类型对象长什么样？
--------------------------

既然 ``PyTypeObject`` 也是一个对象，它的头部必然是 ``PyObject_VAR_HEAD``——也就是说它也是一个可变长对象（``PyVarObject`` ）。

它的完整定义有 **超过 50 个字段**，可以分为几个功能组：

.. code-block:: c

    struct _typeobject {
        PyObject_VAR_HEAD           // PyObject 头部 + ob_size
        const char *tp_name;        // 类型名称，如 "int"
        Py_ssize_t tp_basicsize;    // 该类型的对象占多少字节
        Py_ssize_t tp_itemsize;     // 变长对象每个元素占多少字节

        // ─── 生命周期 ───
        destructor tp_dealloc;      // 对象析构函数
        initproc tp_init;           // __init__
        newfunc tp_new;             // __new__
        allocfunc tp_alloc;         // 内存分配器
        freefunc tp_free;           // 内存释放器

        // ─── 标准操作 ───
        reprfunc tp_repr;           // __repr__
        hashfunc tp_hash;           // __hash__
        ternaryfunc tp_call;        // __call__
        reprfunc tp_str;            // __str__
        getattrofunc tp_getattro;   // __getattr__
        setattrofunc tp_setattro;   // __setattr__

        // ─── 运算符套件 ───
        PyNumberMethods *tp_as_number;     // 数值运算符
        PySequenceMethods *tp_as_sequence;  // 序列运算符
        PyMappingMethods *tp_as_mapping;    // 映射运算符

        // ─── 属性与继承 ───
        PyMethodDef *tp_methods;    // 方法表
        PyMemberDef *tp_members;    // 成员变量表
        PyGetSetDef *tp_getset;     // 属性访问器表
        PyTypeObject *tp_base;      // 基类
        PyObject *tp_bases;         // 基类元组
        PyObject *tp_mro;           // 方法解析顺序

        // ─── 迭代与比较 ───
        richcmpfunc tp_richcompare; // __lt__, __eq__ 等
        getiterfunc tp_iter;        // __iter__
        iternextfunc tp_iternext;   // __next__

        // ─── 弱引用与 GC ───
        Py_ssize_t tp_weaklistoffset;
        traverseproc tp_traverse;   // GC 标记
        inquiry tp_clear;           // GC 清理

        // ─── 标志与元数据 ───
        unsigned long tp_flags;     // 特性标志位
        const char *tp_doc;         // 文档字符串
        unsigned int tp_version_tag;
        ...
    };

.. mermaid::

    mindmap
      PyTypeObject
        标识
          tp_name
          tp_doc
          tp_flags
        内存
          tp_basicsize
          tp_itemsize
          tp_alloc
          tp_free
        生命周期
          tp_new
          tp_init
          tp_dealloc
        操作
          tp_repr
          tp_str
          tp_hash
          tp_call
        运算符
          tp_as_number
          tp_as_sequence
          tp_as_mapping
        属性
          tp_getattro
          tp_setattro
          tp_methods
          tp_getset
        继承
          tp_base
          tp_mro
          tp_bases
        迭代
          tp_iter
          tp_iternext
        GC
          tp_traverse
          tp_clear

．．而是类就是这个表里的一个字段。为了理解这些字段是做什么的，我们来追踪一下 Python 一行代码的执行路径。

第二问：``str(42)`` 发生了什么？
--------------------------------

当你调用 ``str(42)`` 时，CPython 内部经历了这样的旅程：

.. code-block:: c

    // 1. 通过 ob_type 找到 int 的类型对象
    PyTypeObject *type = Py_TYPE(obj);  // → &PyLong_Type

    // 2. 检查 tp_str 字段
    //    （如果 tp_str 为 NULL，就回退到 tp_repr）
    if (type->tp_str != NULL) {
        result = type->tp_str(obj);     // → long_to_decimal_string(obj)
    }

``tp_str`` 字段就是一个**函数指针**，指向将整数转为字符串的 C 函数。

同样的机制适用于所有操作：

.. list-table::
   :header-rows: 1

   * - Python 代码
     - 调用的 C 函数指针
     - 位于 ``PyTypeObject`` 的字段
   * - ``str(x)``
     - ``type->tp_str(x)``
     - ``tp_str``
   * - ``repr(x)``
     - ``type->tp_repr(x)``
     - ``tp_repr``
   * - ``hash(x)``
     - ``type->tp_hash(x)``
     - ``tp_hash``
   * - ``x + y``
     - ``type->tp_as_number->nb_add(x, y)``
     - ``tp_as_number``
   * - ``len(x)``
     - ``type->tp_as_sequence->sq_length(x)``
     - ``tp_as_sequence``
   * - ``x[key]``
     - ``type->tp_as_mapping->mp_subscript(x, key)``
     - ``tp_as_mapping``
   * - ``x(y)``
     - ``type->tp_call(x, y, NULL)``
     - ``tp_call``
   * - ``for i in x``
     - ``type->tp_iter(x)``
     - ``tp_iter``
   * - ``next(it)``
     - ``type->tp_iternext(it)``
     - ``tp_iternext``

.. mermaid::

    flowchart LR
        op["x + y"] --> type["x->ob_type"]
        type --> nb["tp_as_number"]
        nb --> add["nb_add(x, y)"]
        add --> result["整数加法实现"]

这就是所谓的**虚函数表模式**——``PyTypeObject`` 就是 C 语言中的虚函数表。
每个类型的对象共享同一张表，所以多态的开销就是一次指针解引用。

第三问：``tp_flags`` 里有什么？
-------------------------------

``tp_flags`` 是一个位掩码，用来标记这个类型有哪些特性。常见标志：

.. code-block:: c

    #define Py_TPFLAGS_HEAPTYPE       (1UL << 0)   // 堆分配的类型（class 语句创建）
    #define Py_TPFLAGS_BASETYPE       (1UL << 1)   // 可被继承
    #define Py_TPFLAGS_READY          (1UL << 2)   // 类型已初始化
    #define Py_TPFLAGS_HAVE_GC        (1UL << 3)   // 需要垃圾回收追踪
    #define Py_TPFLAGS_LONG_SUBCLASS  (1UL << 4)   // int 的子类
    #define Py_TPFLAGS_LIST_SUBCLASS  (1UL << 5)   // list 的子类
    #define Py_TPFLAGS_TUPLE_SUBCLASS (1UL << 6)   // tuple 的子类
    #define Py_TPFLAGS_MANAGED_DICT   (1UL << 8)   // 使用内置 dict（PEP 412）
    #define Py_TPFLAGS_MATCH_SELF     (1UL << 26)  // PEP 634 match 支持
    ...

你可以用示例脚本看到这些标志的实际值：

.. code-block:: python

    >>> int.__flags__
    2147680256
    >>> bin(2147680256)
    '0b10000000000001000000000000000000'

通过 ``tp_flags``，CPython 可以在运行时判断一个类型是否支持某些特性——比如只有设置了 ``Py_TPFLAGS_HAVE_GC`` 的类型，才会参与垃圾回收的追踪。

第四问：内置类型 vs Python 类
------------------------------

CPython 里有两种"类型"：

**1. 静态类型（Static Type）**——C 语言里定义好的，编译时就存在

.. code-block:: c

    // Python/Python-ast.c 或 Objects/longobject.c
    PyTypeObject PyLong_Type = {
        PyVarObject_HEAD_INIT(&PyType_Type, 0)
        .tp_name = "int",
        .tp_basicsize = sizeof(PyLongObject),
        .tp_dealloc = (destructor)long_dealloc,
        .tp_str = long_to_decimal_string,
        .tp_as_number = &long_as_number,
        // ...
    };

这个结构体是**静态分配**的，不在堆上。它的所有字段在编译时就初始化好了。

**2. 堆类型（Heap Type）**——Python 的 ``class`` 语句创建的

.. code-block:: python

    class MyClass:
        def __str__(self):
            return "hello"

此时 CPython 会：

#. 在堆上分配一个 ``PyHeapTypeObject``
#. 解析 ``class`` 语句中的方法
#. 填充 ``tp_str`` 等函数指针
#. 设置 ``tp_flags`` 中的 ``Py_TPFLAGS_HEAPTYPE``

堆类型使用 ``PyHeapTypeObject`` 结构体——它在 ``PyTypeObject`` 后面还有额外的空间来存储 ``tp_name`` 的字符串、方法表缓存等数据。

.. code-block:: c

    typedef struct _heaptypeobject {
        PyTypeObject ht_type;          // 继承 PyTypeObject
        PyAsyncMethods as_async;
        PyNumberMethods as_number;
        PyMappingMethods as_mapping;
        PySequenceMethods as_sequence;
        PyBufferProcs as_buffer;
        PyObject *ht_name, *ht_slots, *ht_qualname;
        // ...
    } PyHeapTypeObject;

.. mermaid::

    flowchart TD
        subgraph Static["静态类型（C 编译时）"]
            PyLong_Type["PyLong_Type (int)<br/>全局变量，只读"]
            PyUnicode_Type["PyUnicode_Type (str)"]
            PyList_Type["PyList_Type (list)"]
        end
        subgraph Heap["堆类型（运行时创建）"]
            MyClass["MyClass (用户定义的 class)"]
            MyClass2["AnotherClass"]
        end
        PyType_Type["PyType_Type (type)<br/>所有类型的类型"] --> Static
        PyType_Type --> Heap

第五问：MRO 和方法查找是怎么工作的？
---------------------------------------

当你访问 ``obj.method`` 时，CPython 需要找到 ``method`` 的定义。查找过程是这样的：

#. 顺着 ``obj->ob_type`` 找到类型对象
#. 检查 ``tp_dict`` （该类型的属性字典）
#. 如果没找到，按照 ``tp_mro`` （方法解析顺序，Method Resolution Order）向上查找基类
#. 找到后，如果是函数对象，绑定到 ``obj`` 上返回

``tp_mro`` 是一个元组，存着从当前类到 ``object`` 的 C3 线性化顺序。

.. code-block:: python

    >>> class A: pass
    >>> class B(A): pass
    >>> class C(A): pass
    >>> class D(B, C): pass
    >>> D.__mro__
    (<class 'D'>, <class 'B'>, <class 'C'>, <class 'A'>, <class 'object'>)

在 C 层，``tp_mro`` 就是 ``PyTypeObject`` 里的一个 ``PyObject*`` 指针。

.. mermaid::

    flowchart TD
        obj["obj (D 的实例)"] -->|"ob_type"| D["D 的 PyTypeObject"]
        D -->|"tp_mro"| MRO["(D → B → C → A → object)"]
        MRO -->|"依次查找 tp_dict"| B["B.tp_dict"]
        MRO -->|"然后"| C["C.tp_dict"]
        MRO -->|"最后"| A["A.tp_dict"]

第六问：为什么 type(x) 这么快？
-------------------------------

因为 ``type()`` 的 C 实现就是：

.. code-block:: c

    PyObject *
    type_type(PyObject *self, PyObject *args)
    {
        PyObject *obj;
        if (!PyArg_ParseTuple(args, "O", &obj))
            return NULL;
        // 直接读 ob_type 指针！
        Py_INCREF(obj->ob_type);
        return (PyObject *)obj->ob_type;
    }

没有查字典，没有 MRO 遍历，就是从对象的头部读一个指针出来。这就是为什么 Python
的动态类型在运行时几乎零开销——**类型信息就在对象头部的同一个 cache line 里** 。

通过示例脚本验证
----------------

运行 :file:`examples/typeobject_demo.py` 可以看到：

.. code-block:: text

    --- 内置类型 vs 用户类 ---
    int 的 ob_type:         <class 'type'>
    str 的 ob_type:         <class 'type'>
    MyClass 的 ob_type:     <class 'type'>

    --- type 本身 --------------------------------
    type 的 ob_type:        <class 'type'>

    --- 类型字段探针 ----------------------------
    int.tp_name:            int
    str.tp_name:            str
    list.tp_name:           list

    --- MRO 验证 --------------------------------
    D.__mro__[0] = <class 'D'>
    D.__mro__[1] = <class 'B'>
    D.__mro__[2] = <class 'C'>
    D.__mro__[3] = <class 'A'>
    D.__mro__[4] = <class 'object'>

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 类型对象也是对象吗？
     - 是的，``PyTypeObject`` 以 ``PyObject_VAR_HEAD`` 开头
   * - Python 的操作是怎么分发到 C 函数的？
     - 通过 ``PyTypeObject`` 中的函数指针（tp_str, tp_call 等）
   * - 内置类型和 Python class 有什么区别？
     - 内置类型是静态分配的；Python class 是堆上的 ``PyHeapTypeObject``
   * - MRO 存在哪里？
     - ``tp_mro`` 字段，存着 C3 线性化后的类型元组
   * - ``type(x)`` 为什么快？
     - 直接读 ``x->ob_type``，一次指针解引用

参考资料
--------

- :pep:`252` — 类型系统与描述符协议
- :pep:`573` — 模块级状态的 C 访问
- :file:`Include/object.h` — ``PyTypeObject`` 结构定义
- :file:`Objects/typeobject.c` — 类型创建与 MRO 计算

现在你理解了类型系统的骨架。下一篇我们将深入 **引用计数**——看看 ``Py_INCREF`` / ``Py_DECREF`` 的具体实现，以及 3.14 中平衡引用计数（BRC）带来的变化。
