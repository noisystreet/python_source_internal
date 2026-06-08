.. _objects-unicode:

内置类型 — str (PyUnicodeObject)
====================================

.. epigraph::

   "A common language creates a common understanding."

   -- Vint Cerf, co-creator of TCP/IP


Python 的 ``str`` 是最常用的内置类型之一，也是实现最复杂的。为了在不同字符集之间做到
**内存高效** ，CPython 根据字符串内容自动选择三种内部表示之一。

从一道题开始
------------

.. code-block:: python

    >>> s1 = "hello"         # 纯 ASCII
    >>> s2 = "你好"          # 中文（需要 2 字节）
    >>> s3 = "😊"            # Emoji（需要 4 字节）
    >>> s4 = "a" * 1000000   # 100 万个字符

这四个字符串在内存中的占用天差地别。CPython 会根据字符串中的最大字符自动选择
最紧凑的存储方式——每个字符 1、2 或 4 字节。

.. mermaid::

    graph TD
        s["新字符串"] --> check{"最大码点?"}
        check -->|"U+0000-U+00FF"| ascii["1 字节/字符 (Latin-1)"]
        check -->|"U+0100-U+FFFF"| ucs2["2 字节/字符 (UCS-2)"]
        check -->|"U+10000-U+10FFFF"| ucs4["4 字节/字符 (UCS-4)"]
        ascii -->|"如果全部 ASCII"| compact["紧凑: 字符数据紧跟在头部后"]
        ucs2 --> compact
        ucs4 --> compact

第一问：str 的三种内部结构
--------------------------

CPython 3.3+（PEP 393）引入了灵活字符串表示，根据内容使用三种结构体之一：

.. code-block:: c

    /* 1. 纯 ASCII — PyASCIIObject */
    typedef struct {
        PyObject_HEAD
        Py_ssize_t length;       // 字符数
        Py_hash_t hash;          // 哈希值，-1 表示未计算
        struct {
            unsigned int interned:2;  // 是否被 intern
            unsigned int kind:3;     // 1/2/4 字节每字符
            unsigned int compact:1;  // 是否紧凑
            unsigned int ascii:1;    // 是否纯 ASCII
            unsigned int ready:1;    // 是否已准备好
            // ...
        } state;
        // wchar_t* data;  // 字符数据紧跟在后面（不是指针！）
    } PyASCIIObject;

    /* 2. 紧凑非 ASCII — PyCompactUnicodeObject */
    typedef struct {
        PyASCIIObject _base;     // 继承 ASCII 头部
        Py_ssize_t utf8_length;  // UTF-8 编码长度
        char *utf8;              // UTF-8 缓存指针
    } PyCompactUnicodeObject;

    /* 3. 旧式（子类）— PyUnicodeObject */
    typedef struct {
        PyCompactUnicodeObject _base;
        PyObject *str_data;      // 指向外部数据块
    } PyUnicodeObject;

.. mermaid::

    graph BT
        PyASCIIObject["PyASCIIObject<br/>纯 ASCII (1 字节/字符)"]
        PyCompactUnicodeObject["PyCompactUnicodeObject<br/>紧凑非 ASCII (1/2/4 字节/字符)"]
        PyUnicodeObject["PyUnicodeObject<br/>旧式 (数据在外部)"]
        subgraph Data["字符数据位置"]
            inline["紧跟在结构体后面"]
            external["在堆上另一块内存"]
        end
        PyASCIIObject --> inline
        PyCompactUnicodeObject --> inline
        PyUnicodeObject --> external

第二问：三种字符宽度
--------------------

``state.kind`` 字段决定每个字符用多少字节：

.. list-table::
   :header-rows: 1

   * - kind
     - 每字符字节数
     - 可表示的字符范围
     - 对应 C 类型
     - 例子
   * - ``1``
     - 1
     - U+0000 ~ U+00FF (Latin-1)
     - ``Py_UCS1``
     - "hello", "café"
   * - ``2``
     - 2
     - U+0000 ~ U+FFFF (BMP)
     - ``Py_UCS2``
     - "你好", "世界"
   * - ``4``
     - 4
     - U+0000 ~ U+10FFFF (全部)
     - ``Py_UCS4``
     - "😊", "𝄞"

CPython 在创建字符串时自动选择最紧凑的表示。例如 ``"hello"`` 用 1 字节/字符，
``"你好"`` 用 2 字节/字符。选择逻辑在 ``PyUnicode_New`` 中：

.. code-block:: c

    PyObject *PyUnicode_New(Py_ssize_t size, Py_UCS4 maxchar)
    {
        if (maxchar < 128) {
            // PyASCIIObject，1 字节/字符
        } else if (maxchar < 256) {
            // PyASCIIObject 但 state.ascii = 0，1 字节/字符
        } else if (maxchar < 65536) {
            // PyCompactUnicodeObject，2 字节/字符
        } else {
            // PyCompactUnicodeObject，4 字节/字符
        }
    }

第三问：字符串 interning
-------------------------

CPython 会对某些字符串做 **intern** （驻留）处理——相同的字符串只存一份， ``is`` 比较返回 ``True`` ：

.. code-block:: python

    >>> a = "hello"
    >>> b = "hello"
    >>> a is b
    True   # 被 intern 了！
    >>> c = "hello world!"
    >>> d = "hello world!"
    >>> c is d
    False  # 太长，未被 intern

哪些字符串会被 intern？

- 标识符风格的字符串（变量名、属性名、方法名）
- 代码对象中的 ``co_names`` 和 ``co_consts`` 中的字符串
- 短的、看起来像标识符的字符串字面量

在 C 层，intern 通过 ``PyUnicode_InternInPlace`` 实现：

.. code-block:: c

    void PyUnicode_InternInPlace(PyObject **p)
    {
        PyObject *s = *p;
        // 查找 intern 字典
        PyObject *interned = interp->unicode.ids.dict;
        PyObject *t = PyDict_GetItem(interned, s);
        if (t != NULL) {
            // 已有相同字符串，复用
            Py_INCREF(t);
            Py_SETREF(*p, t);
        } else {
            // 新字符串，加入字典
            PyDict_SetItem(interned, s, s);
            // 设置 interned 标志
            ((PyASCIIObject *)s)->state.interned = 1;
        }
    }

被 intern 的字符串有两个特殊之处：

- 引用计数不计入字典中的两次引用（避免"字典引用了字符串 → 字符串引用计数永不为 0"的死锁）
- ``is`` 比较等价于指针比较——比 ``==`` （需逐字符比较）快得多

第四问：哈希缓存
----------------

每个 ``PyASCIIObject`` 都有一个 ``hash`` 字段。字符串的哈希值在 **第一次计算后就被缓存** ：

.. code-block:: c

    // unicode_hash 实现
    static Py_hash_t unicode_hash(PyObject *self)
    {
        PyASCIIObject *ascii = (PyASCIIObject *)self;
        if (ascii->hash != -1) {
            return ascii->hash;  // 已有缓存
        }
        // 计算并缓存
        ascii->hash = hash_func(data, length);
        return ascii->hash;
    }

这意味着：

- ``hash(s)`` 第一次调用时做一次完整计算
- 之后直接返回缓存值，O(1)
- 这也意味着 Python 字符串不可变——如果字符串可变，哈希缓存就无效了

第五问：字符串拼接的陷阱
-------------------------

.. code-block:: python

    s = ""
    for i in range(100000):
        s += str(i)   # 性能灾难！

每次 ``+=`` 都创建一个新字符串，复制旧内容。复杂度是 O(n²)。因为字符串是不可变的。

CPython 在 3.14 中对此做了优化——``s += str(i)`` 如果 ``s`` 只有这一个引用，
且缓冲区足够，会"就地"修改（虽然逻辑上仍不可变，但内部可以复用缓冲区）。

但正确的做法仍然是使用列表：

.. code-block:: python

    parts = [str(i) for i in range(100000)]
    s = "".join(parts)  # O(n)，预先计算总长度一次分配

``"".join()`` 在 C 层遍历列表，计算总长度，一次分配内存，然后逐个拷贝字符。

第六问：Python 的 str 和 bytes 有什么关系？
-------------------------------------------

在 C 层， ``str`` 和 ``bytes`` 是完全不同的类型：

- ``str`` = ``PyUnicodeObject`` （Unicode 码点序列）
- ``bytes`` = ``PyBytesObject`` （字节序列）

当你调用 ``"你好".encode("utf-8")`` 时，CPython 会：

#. 从 ``str`` 对象中取出字符数据
#. 根据编码方式（UTF-8）将每个码点转为 1-4 个字节
#. 创建一个新的 ``PyBytesObject``

``decode`` 则相反：将字节序列按编码方式解析为码点序列。

通过示例脚本验证
----------------

运行 :file:`examples/unicode_demo.py`：

.. code-block:: text

    --- 字符串的内部表示 ---
    'hello':    kind=1, ascii=True,  size=5,  每字符 1 字节
    '你好':      kind=2, ascii=False, size=2,  每字符 2 字节
    '😊':        kind=4, ascii=False, size=1,  每字符 4 字节

    --- Interning ---
    'hello' is 'hello': True (被 intern)
    'hello world!!!' is 'hello world!!!': True (CPython 3.14 intern 更多)

    --- 拼接性能 ---
    join 方法: 0.01s
    += 循环:   0.85s

    --- 哈希缓存 ---
    第一次 hash(s): 计算
    第二次 hash(s): 缓存命中

小结
----

.. list-table::
   :header-rows: 1

   * - 特性
     - 实现方式
   * - 紧凑表示
     - 按最大字符自动选 1/2/4 字节/字符
   * - 三种结构体
     - PyASCIIObject / PyCompactUnicodeObject / PyUnicodeObject
   * - Interning
     - 字典管理唯一实例， ``is`` 变指针比较
   * - 哈希缓存
     - ``PyASCIIObject.hash`` ，-1 表示未计算
   * - 拼接优化
     - 单引用时复用缓冲区，但推荐 ``"".join()``

参考资料
--------

- :ref:`objects-pyobject` — PyVarObject 与变长字符串的 ob_size
- :ref:`runtime-codecs` — 编解码系统与字符串转换
- :file:`Objects/unicodeobject.c` — Unicode 实现
- :pep:`393` — 灵活字符串表示
- :pep:`623` — 压缩 Unicode 内部表示
