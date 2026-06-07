PyObject 结构
=============

.. 本文的写作风格：从最直观的问题出发，每步只加一个新概念，逐步深入。
   请保持这种「浅入深出」的叙事方式。

从一道题开始
------------

假设你写了这样一行代码：

.. code-block:: python

    x = 42

现在，Python 的 **进程内存** 里发生了什么？

- ``42`` 是一个整数——一个"对象"（object）。
- ``x`` 是一个变量名——它指向那个对象。
- 但你有没有想过：**这个对象在内存里长什么样？** 占几个字节？里面放了什么？

这一节，我们就从这个问题出发，一层层地拆开 CPython 最核心的数据结构——``PyObject``。

.. note::

   **建议配合示例运行**

   本章配套脚本 :file:`examples/pyobject_layout.py` 可以让你实时看到自己 Python 进程里对象的内存布局。
   建议打开终端，边读边跑：

   .. code-block:: bash

       python examples/pyobject_layout.py

第一问：一个 Python 对象最少要存什么？
---------------------------------------

假设让你用 C 语言设计一个"通用对象系统"，什么信息是必不可少的？

至少需要两样东西：

#. **这个对象的类型是什么**——整数、字符串、还是列表？知道了类型才知道怎么操作它。
#. **这个对象还被谁引用着**——没人用就该回收了，有人用就不能回收。

就这两个？对，就这两个。CPython 的 ``PyObject`` 核心就只做了这两件事：

.. code-block:: c

    struct _object {
        Py_ssize_t ob_refcnt;   /* 有多少个引用指向我？*/
        PyTypeObject *ob_type;  /* 我是什么类型？*/
    };

.. mermaid::

    graph LR
        Box["PyObject<br/>┌──────────────┐<br/>│ ob_refcnt    │  ← 引用计数<br/>│ ob_type      │  ← 类型指针<br/>└──────────────┘"]
        Box --> Ref["被引用了多少次？"]
        Box --> Type["我是什么类型？"]

就这么简单。**任何 Python 对象的 C 结构体，头部必然是这两个字段。**

你可以自己验证。运行 ``examples/pyobject_layout.py``，其中 ``read_pyobject_header``
函数直接用 ``ctypes`` 读取对象所在内存的前几个字节：

.. code-block:: python

    refcnt = c_uint32.from_address(id(x)).value   # 读前 4 字节
    ob_type = c_void_p.from_address(id(x) + 8).value  # 读偏移 8 处的 8 字节

.. note::

   为什么偏移是 8 而不是 4？因为 64 位系统上对齐规则不一样。我们马上会看到。

第二问：64 位系统上 PyObject 到底有多大？
------------------------------------------

你可能会想：既然只有两个字段，那就 4 字节 + 8 字节 = 12 字节？

不对。是 **16 字节**。

原因有两个：

#. 内存对齐：``ob_type`` 是 8 字节指针，必须从 8 的倍数地址开始。所以 ``ob_refcnt`` 虽然只占 4 字节，但后面要填充 4 字节空白。
#. 额外字段：CPython 还在 64 位系统上偷偷塞了两个 2 字节的字段——``ob_flags`` 和 ``ob_overflow``，塞在 ``ob_refcnt`` 后面本来要浪费掉的填充空间里。

所以 64 位系统上的真实布局是：

.. code-block:: c

    struct _object {
        union {
            PY_INT64_T ob_refcnt_full;  /* 凑齐 8 字节 */
            struct {
                uint32_t ob_refcnt;     /* +0: 引用计数 (4B) */
                uint16_t ob_overflow;   /* +4: 溢出计数 (2B) */
                uint16_t ob_flags;      /* +6: 标志位   (2B) */
            };
        };                              /* 合计 8 字节 */
        PyTypeObject *ob_type;          /* +8: 类型指针 (8B) */
    };                                  /* 总计 16 字节 */

.. mermaid::

    graph LR
        subgraph Mem["内存布局 (64位, 小端序)"]
            A["+0: ob_refcnt (4B)"]
            B["+4: ob_flags (2B)"]
            C["+6: ob_overflow (2B)"]
            D["+8: ob_type → (8B)"]
        end
        A --> B --> C --> D

我们之前用 ``ctypes`` 读偏移 +0 和 +8 是没错的——+4 到 +7 被 ``ob_flags`` 和 ``ob_overflow`` 占了，但它们在大多数场景下你不会直接关心。

.. tip::

   你现在可以试试运行示例脚本，看看自己系统上 ``42`` 这个整数的引用计数是多少：

   ::

       refcount: 4294967295 (0xffffffff) [immortal]

   如果看到 ``4294967295`` 这个数字——别慌，它不是"被引用了 42 亿次"，而是「immortal 标记」。我们后面会讲。

第三问：可变长的对象怎么办？
----------------------------

上面说的 ``PyObject`` 是"固定大小"的头部。那像字符串、列表、字典这种长度可变的对象呢？

CPython 的做法是：在 ``PyObject`` 基础上再加一个 ``ob_size`` 字段，记录"元素的个数"：

.. code-block:: c

    typedef struct {
        PyObject ob_base;       /* PyObject 头部 (16B) */
        Py_ssize_t ob_size;     /* 元素个数 (8B) */
    } PyVarObject;              /* 总计 24 字节 */

所以当你写 ``s = "Hello"`` 时，字符串对象的前 24 字节是：

.. mermaid::

    graph LR
        subgraph PyVarObject["字符串对象 前 24 字节"]
            A["ob_refcnt (4B)"]
            B["ob_flags|overflow (4B)"]
            C["ob_type → &PyUnicode_Type (8B)"]
            D["ob_size = 5 (8B)"]
        end
        A --> B --> C --> D

用示例脚本验证：

.. code-block:: python

    # read_pyvarobject_size 读取 +16 偏移处的 8 字节
    strlen = read_pyvarobject_size(id("Hello CPython"))
    print(strlen)  # 输出: 13

.. note::

   注意 ``ob_size`` 是"元素个数"而不是"字节数"——对字符串是字符数，对列表是元素个数，对字节串是字节数。

第四问：引用计数是怎么工作的？
------------------------------

回到最开始的问题：**当没人用这个对象了，会发生什么？**

CPython 用"引用计数"这个简单的机制来解决：

.. code-block:: c

    // Py_INCREF: 增加引用计数
    #define Py_INCREF(op) ((op)->ob_refcnt++)

    // Py_DECREF: 减少引用计数，减到 0 就回收
    #define Py_DECREF(op) \
        if (--(op)->ob_refcnt == 0) \
            _Py_Dealloc(op)  /* 真正释放内存 */

每一步赋值、传参、容器操作，CPython 都在背后默默地 ``Py_INCREF`` / ``Py_DECREF``。

用脚本看引用计数的变化：

.. code-block:: python

    lst = [1, 2, 3]
    # refcount = 1

    lst_ref = lst   # 增加一个引用
    # refcount = 2

    del lst_ref     # 减少一个引用
    # refcount = 1

运行 ``examples/pyobject_layout.py`` 可以实时看到这个变化过程。

.. warning::

   用 ``sys.getrefcount()`` 拿到的值会比实际多 1——因为传参本身也产生了一次临时引用。

再深一层：Immortal 对象
^^^^^^^^^^^^^^^^^^^^^^^^

问题来了：有些对象是"永远不可能被回收"的。比如 ``None``、``True``、``False``，以及小整数池里的 ``-5`` 到 ``257``。

如果每次 ``Py_INCREF`` / ``Py_DECREF`` 都对它们操作——即使什么也不变——也是白白浪费 CPU。尤其是在多线程场景下，引用计数的原子操作开销很大。

CPython 3.12+ 的解决方案是 **Immortal（不可变）对象**：

- 把引用计数设成一个**极高的值**（64 位上是 ``3ULL << 30`` ≈ 32 亿）
- ``Py_INCREF`` 检测到计数处于"高位区"，直接跳过
- ``Py_DECREF`` 同理

.. code-block:: c

    /* 64 位系统的不可变阈值 */
    #define _Py_IMMORTAL_INITIAL_REFCNT (3ULL << 30)  /* ≈ 3.2G */
    #define _Py_IMMORTAL_MINIMUM_REFCNT (1ULL << 31)  /* ≈ 2.1G */

你可以看示例脚本的输出：

::

    --- 小整数池 (interned) ---
    值:        42
    refcount:  4294967295 (0xffffffff) [immortal]

    --- None 对象 (单例) ---
    refcount: 4294967295 (0xffffffff) [immortal]

``4294967295`` = ``0xFFFFFFFF`` = 32 位全 1——这就是"我是不朽的"标记。

.. mermaid::

    flowchart LR
        A["Py_INCREF(obj)"] --> B{"ob_refcnt >= 2^31?"}
        B -->|"是 (immortal)"| C["什么都不做"]
        B -->|"否 (普通)"| D["ob_refcnt++"]

第五问：ob_type 指向哪里？
--------------------------

``ob_type`` 是一个指针，指向一个 ``PyTypeObject`` 结构体——也就是 Python 里的"类型"。

当你写 ``type(x)`` 时，CPython 实际上做的就是：

.. code-block:: c

    x->ob_type  // 直接读指针

这就是为什么 Python 的 ``type()`` 这么快——它只是从对象的头部读了一个指针出来。

每个内置类型（``int``、``str``、``list``……）都有一个全局唯一的 ``PyTypeObject`` 实例，
比如 ``PyLong_Type``、``PyUnicode_Type``、``PyList_Type``。

.. mermaid::

    flowchart TD
        subgraph Objects["多个整数对象"]
            A["42"]
            B["99999"]
            C["-1"]
        end
        A -->|"ob_type 指向"| T["PyLong_Type<br/>(全局唯一)"]
        B -->|"ob_type 指向"| T
        C -->|"ob_type 指向"| T
        T -->|"tp_name"| N["'int'"]
        T -->|"tp_add"| ADD["整数加法实现"]
        T -->|"tp_str"| STR["整数转字符串实现"]

这就是 Python "一切皆对象，对象有类型"的 C 层真相——每个对象用 ``ob_type`` 指针标出自己的类型，
类型对象里存着这个类型"能做什么"（加、减、转字符串……）。

再深入一点：为什么 Python 里没有"值类型"？
------------------------------------------

很多语言（C、Rust、Go）中，基本类型（int、float）是直接存值的，不经过堆分配。
但 Python 里一切都是对象——也就是说，**每个整数都在堆上**。

你可以验证：

.. code-block:: python

    >>> a = 42
    >>> b = 42
    >>> a is b
    True   # 因为小整数池复用了同一个 PyObject

    >>> c = 99999
    >>> d = 99999
    >>> c is d
    False  # 大整数每次创建新的 PyObject

CPython 为了缓解"一切皆对象"的性能代价，用了几个技巧：

- **小整数池**：``-5`` 到 ``257`` 的整数在启动时预先创建好，永远复用
- **immortal 标记**：常用单例（``None``、小整数）标记为 immortal，跳过引用计数操作
- **``PyLongObject`` 的变长设计**：大整数用 ``ob_size`` 的正负表示符号，而不是再包装一层

这些技巧的根基，都是那个最简单的 16 字节头部——``PyObject``。

CPython 的"继承"——用 C 实现的单继承
--------------------------------------

最后说说 CPython 里最重要的一种设计模式。

当你定义一个具体的类型（比如整数），它的 C 结构体长这样：

.. code-block:: c

    typedef struct {
        PyObject ob_base;        /* 先放 PyObject 头部 (16B) */
        uint32_t ob_digit[1];    /* 再放自己的数据 */
    } PyLongObject;

如果想把 ``PyLongObject*`` 当作 ``PyObject*`` 用，怎么办？

**直接强转**。因为 ``PyLongObject`` 的第一个字段就是 ``ob_base``（即 ``PyObject``），
所以 ``(PyObject*)long_obj`` 就是合法的。这就是 C 语言里手动实现的"单继承"——所有具体的对象类型，
第一个字段必须是 ``PyObject_HEAD``（展开后就是 ``PyObject ob_base``）。

.. mermaid::

    flowchart BT
        PyLongObject -->|"第一个字段"| ob_base["PyObject ob_base"]
        PyDictObject -->|"第一个字段"| ob_base
        PyListObject -->|"第一个字段"| PyVarObject["PyVarObject ob_base<br/>(包含 PyObject 内嵌)"]
        PyUnicodeObject -->|"第一个字段"| PyVarObject

所以不管传进来的是什么类型，CPython 永远可以把它当作 ``PyObject*`` 来处理——读 ``ob_refcnt`` 和 ``ob_type`` 就够了。
需要做具体类型操作时，再 ``(PyLongObject*)obj`` 转回去。

这就是 CPython 对象模型的**核心设计**：**通过统一的头部实现多态，所有对象共享同一套内存管理机制**。

通过示例脚本验证
----------------

运行 :file:`examples/pyobject_layout.py`：

.. code-block:: text

    --- PyObject 头部大小 ---
    64 位系统上 PyObject = 16 字节
    PyVarObject = 24 字节（比 PyObject 多 ob_size）

    --- 具体类型大小 ---
    int: 28 字节
    str: 49 字节
    list: 56 字节
    dict: 56 字节
    tuple: 40 字节 (空)
    object(): 32 字节

    --- 引用计数与类型 ---
    obj 的引用计数: 1
    obj 的类型: <class 'object'>

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - PyObject 最少要存什么？
     - 引用计数 + 类型指针
   * - 64 位系统上多大？
     - 16 字节（含 ob_flags / ob_overflow）
   * - 可变长度对象呢？
     - 加 ``ob_size`` → ``PyVarObject``，24 字节
   * - 引用计数怎么工作？
     - ``Py_INCREF`` / ``Py_DECREF``，减到 0 就回收
   * - 什么是 Immortal？
     - 引用计数设极大值，跳过 INC/DEC 操作
   * - ob_type 有什么用？
     - 指向全局类型对象，实现动态类型
   * - 怎么实现"一切皆对象"？
     - 每个具体结构以 ``PyObject`` 开头，直接强转

参考资料
--------

- :pep:`683` — 永生对象（Immortal Objects）
- :file:`Include/object.h` — ``PyObject`` 与 ``PyVarObject`` 结构定义
- :file:`Include/refcount.h` — 引用计数宏实现
- `CPython 对象内存布局 <https://docs.python.org/3/c-api/structures.html>`__

