弱引用 —— 引用它但不留住它
===============================

在引用计数篇我们知道了：只要有人引用一个对象，它就不会被回收。但有时我们
**想引用一个对象，同时又不想阻止它被回收** 。比如缓存、观察者模式、循环引用的打破。

这就是弱引用（weak reference）的用途。

从一道题开始
------------

.. code-block:: python

    import weakref

    class BigObject:
        pass

    obj = BigObject()
    ref = weakref.ref(obj)   # 创建一个弱引用

    print(ref())   # <__main__.BigObject object at 0x...> — 对象还活着
    del obj        # 删除唯一的强引用
    print(ref())   # None — 对象已被回收

``weakref.ref(obj)`` 创建了一个**弱引用**——它指向 ``obj``，但不增加 ``obj`` 的引用计数。
当所有强引用消失后，对象被回收，弱引用自动变成 ``None`` 。

.. mermaid::

    flowchart LR
        obj["强引用 obj"] -->|"refcount = 1"| target["BigObject 实例"]
        ref["弱引用 ref"] -.->|"refcount 不变"| target
        del_obj["del obj"] -->|"refcount = 0"| dead["对象被回收"]
        dead -->|"ref() = None"| none["弱引用自动变 None"]

第一问：弱引用的 C 结构长什么样？
---------------------------------

弱引用本身也是一个对象——``PyWeakReference`` ：

.. code-block:: c

    struct _PyWeakReference {
        PyObject_HEAD

        PyObject *wr_object;    // 被引用的对象，或 Py_None（已失效）
        PyObject *wr_callback;  // 对象被回收时调用的回调，或 NULL

        Py_hash_t hash;         // 被引用对象的哈希值缓存

        // 双向链表指针
        PyWeakReference *wr_prev;
        PyWeakReference *wr_next;

        vectorcallfunc vectorcall;
    };

关键点：

- ``wr_object`` 指向被引用对象。但这是一个**隐式引用**——``wr_object`` 的存在不计入 ``ob_refcnt``
- 每个可以被弱引用的对象都有一个**弱引用链表头**，通过 ``tp_weaklistoffset`` 定位
- 当 ``wr_object`` 被回收时，CPython 遍历这个链表，把每个 ``PyWeakReference`` 的 ``wr_object`` 设为 ``Py_None``，并调用回调

.. mermaid::

    flowchart LR
        subgraph Object["可弱引用对象"]
            weaklist["tp_weaklistoffset → 链表头"]
        end
        weaklist --> wr1["weakref #1<br/>wr_object → Object"]
        weaklist --> wr2["weakref #2<br/>wr_object → Object"]
        weaklist --> wr3["weakref #3<br/>wr_object → Object"]
        wr1 <--> wr2
        wr2 <--> wr3

第二问：哪些对象可以被弱引用？哪些不行？
----------------------------------------

不是所有 Python 对象都能被弱引用。只有 ``tp_flags`` 中设置了 ``Py_TPFLAGS_MANAGED_WEAKREF``
（3.12+ 的自动管理方式）或手动设置了 ``tp_weaklistoffset`` 的类型才支持。

.. code-block:: python

    import weakref

    class MyClass:
        pass

    obj = MyClass()
    ref = weakref.ref(obj)  # 可以 — 用户定义的 class 默认支持

    ref = weakref.ref([1, 2, 3])  # TypeError! list 不支持弱引用

    ref = weakref.ref({"key": "value"})  # TypeError! dict 也不行

    ref = weakref.ref((1, 2))  # TypeError! tuple 也不行

为什么内置类型不支持？因为**性能** 。如果每个 ``list`` 、``dict`` 、``tuple`` 都要预留
一个弱引用链表头，会浪费大量内存——毕竟绝大多数列表永远不会被弱引用。

CPython 3.12 之前，类型需要手动设置 ``tp_weaklistoffset`` 。3.12+ 引入了
``Py_TPFLAGS_MANAGED_WEAKREF``，由 VM 自动管理弱引用链表的位置。

支持弱引用的常见类型：

- 用户自定义类（``class`` 语句创建的）
- ``type`` 本身
- ``function``
- ``generator``
- ``property`` 、``staticmethod`` 、``classmethod``
- ``set`` 、``frozenset`` （但 ``list`` 、``dict`` 、``tuple`` 不行）

第三问：弱引用是如何"自动失效"的？
----------------------------------

当一个对象的引用计数降为 0 时，CPython 的 ``tp_dealloc`` 流程中会调用
``PyObject_ClearWeakRefs`` ：

.. code-block:: c

    void PyObject_ClearWeakRefs(PyObject *object)
    {
        PyWeakReference **list = _PyObject_GET_WEAKREFS_LISTPTR(object);

        // 如果弱引用链表为空，直接返回
        if (*list == NULL)
            return;

        // 遍历链表
        PyWeakReference *wr = *list;
        while (wr != NULL) {
            PyWeakReference *next = wr->wr_next;

            // 把 wr_object 设回 Py_None（标记失效）
            wr->wr_object = Py_None;
            // 如果有关联的回调，调用它
            if (wr->wr_callback != NULL) {
                PyObject *cb = wr->wr_callback;
                PyObject *result = PyObject_CallOneArg(cb, wr);
                // ...
            }

            wr = next;
        }

        // 链表已空
        *list = NULL;
    }

这就是弱引用"自动失效"的原理——**在对象析构时，遍历所有指向它的弱引用，把它们清掉** 。

.. mermaid::

    flowchart TD
        dealloc["tp_dealloc 被调用"] --> check["PyObject_ClearWeakRefs"]
        check --> chain{"是否有弱引用?"}
        chain -->|"无"| free["正常释放内存"]
        chain -->|"有"| foreach["遍历弱引用链表"]
        foreach --> set_none["将 wr_object 设为 Py_None"]
        set_none --> has_cb{"有回调?"}
        has_cb -->|"有"| call_cb["调用回调函数"]
        has_cb -->|"无"| next_wr["处理下一个"]
        call_cb --> next_wr
        next_wr -->|"全部处理完"| free

第四问：weakref.ref、weakref.proxy 和 weakref.WeakValueDictionary 有什么区别？
----------------------------------------------------------------------------------

CPython 在 Python 层的 ``weakref`` 模块之上提供了几种不同用法的弱引用类型：

**weakref.ref(obj[, callback])** — 最基本的弱引用

.. code-block:: python

    ref = weakref.ref(obj)
    obj2 = ref()       # 通过 ref() 获取对象，如果对象还活着
    if obj2 is not None:
        # 对象还活着，可以安全使用
        pass

**weakref.proxy(obj[, callback])** — 透明代理

.. code-block:: python

    proxy = weakref.proxy(obj)
    proxy.method()     # 直接当 obj 用，不用调用 ref()
    # 但如果 obj 已死，访问代理会抛 ReferenceError

**weakref.WeakValueDictionary** — 值弱引用的字典

.. code-block:: python

    wvd = weakref.WeakValueDictionary()
    wvd['key'] = obj   # 值以弱引用存储
    # 当 obj 在其他地方被删除后，wvd 自动移除该条目

**weakref.WeakKeyDictionary** — 键弱引用的字典

**weakref.WeakSet** — 元素弱引用的集合

在 C 层，``weakref.proxy`` 对应 ``_PyWeakref_ProxyType``，它的 ``tp_getattro``
方法在返回属性之前会检查 ``wr_object`` 是否还活着。

第五问：弱引用在 CPython 源码内部怎么用？
------------------------------------------

CPython 自身大量使用弱引用：

**1. 函数对象的弱引用链表**

每个 ``PyFunctionObject`` 都支持弱引用。PEP 681（``@override`` 检查）等新特性
通过 ``PyFunction_AddWatcher`` 注册回调，这些回调以弱引用的方式跟踪函数生命周期。

**2. 类型的子类追踪**

.. code-block:: c

    // 在 typeobject.c 中
    PyTypeObject *type = ...;
    // type->tp_subclasses 是一个弱引用字典
    // 当一个子类被销毁时，它自动从父类的 tp_subclasses 中移除
    // 不会因为"父类记得子类"而导致子类无法被回收

**3. 模块的弱引用**

``sys.modules`` 中的模块可以被弱引用。这对于需要保持模块引用但又不阻止模块
重新加载的场景非常有用。

第六问：弱引用和 gc 有什么关系？
--------------------------------

弱引用是打破循环引用的一个重要工具，但不是 gc 的主要手段：

- **引用计数** 无法处理循环引用（A→B→A），因为它们的引用计数永远不会到 0
- **gc** 定期扫描并回收循环引用的对象
- **弱引用** 可以在设计层面避免循环引用——如果 A 弱引用 B，就不会形成强循环

但弱引用和 gc 有一个微妙交互：当一个对象同时有弱引用回调并形成循环引用时，
gc 会先调用 ``tp_clear`` （解除循环），再调用 ``PyObject_ClearWeakRefs`` 。
CPython 保证回调在安全的时间点被调用。

.. code-block:: c

    // gcmodule.c 中 gc 处理弱引用的策略
    static int
    gc_traverse(PyObject *op, visitproc visit, void *arg)
    {
        // GC 标记阶段遍历弱引用链表中的对象
        // 但不会通过弱引用"救活"一个收集到的对象
    }

通过示例脚本验证
----------------

运行 :file:`examples/weakref_demo.py`：

.. code-block:: text

    --- 弱引用基础 ---
    ref() 返回: <BigObject object at 0x...>
    删除强引用后 ref() 返回: None

    --- 回调函数 ---
    对象被回收了！调用回调

    --- WeakValueDictionary ---
    删除前: {'key': <BigObject object at 0x...>}
    删除后: {}

    --- 哪些类型支持弱引用 ---
    MyClass:     ✅ 支持
    list:        ❌ 不支持
    dict:        ❌ 不支持
    tuple:       ❌ 不支持
    set:         ✅ 支持
    function:    ✅ 支持
    generator:   ✅ 支持

    --- 弱引用和循环引用 ---
    使用弱引用可以避免循环引用导致的泄漏

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 弱引用怎么做到"不增加引用计数"？
     - ``wr_object`` 是隐式引用
   * - 弱引用怎么自动失效？
     - 对象析构时调用 ``PyObject_ClearWeakRefs`` 遍历链表
   * - 哪些类型支持弱引用？
     - 用户 class、function、generator、set 等
   * - 哪些不支持？
     - list、dict、tuple、int、str（性能原因）
   * - weakref.proxy 和 ref 的区别？
     - proxy 透明代理，访问已死对象抛 ReferenceError
   * - CPython 内部哪里用了弱引用？
     - 类型子类追踪（tp_subclasses）、函数 watcher 等
