内置类型 — int (PyLongObject)
================================

Python 的 ``int`` 没有上限——你可以写 ``2 ** 1000000``，它不会溢出。
这背后是一个**变长大整数**实现。

从一道题开始
------------

.. code-block:: python

    >>> a = 42
    >>> b = 2 ** 1000

这两个看起来都是整数，但它们在内存中的差别巨大。``a`` 只需要一个 30 位的 digit 就能存下，
``b`` 需要 34 个 digit。CPython 的 ``PyLongObject`` 正是为此设计的——它可以根据数值大小
动态分配空间。

.. mermaid::

    graph LR
        subgraph SmallInt["小整数 (compact)"]
            obj_hdr["PyObject_HEAD (16B)"]
            tag_small["lv_tag = 值本身"]
        end
        subgraph BigInt["大整数 (多 digit)"]
            hdr["PyObject_HEAD (16B)"]
            tag_big["lv_tag = 位数 + 符号"]
            d0["ob_digit[0]"]
            d1["ob_digit[1]"]
            d2["..."]
        end
        SmallInt -->|"30 位以内"| BigInt

第一问：PyLongObject 的结构
----------------------------

.. code-block:: c

    typedef struct _PyLongValue {
        uintptr_t lv_tag;      // 高位: 位数, 低位: 符号和标志
        digit ob_digit[1];     // 变长 digit 数组
    } _PyLongValue;

    struct _longobject {
        PyObject_HEAD           // PyObject 头部 (16B)
        _PyLongValue long_value;// tag + digit 数组
    };

核心在于 ``lv_tag`` 这个字段，它是一个位域：

.. code-block:: text

    高位 (bits 3+)         低位 (bits 0-2)
    ┌─────────────────┐  ┌──────────────┐
    │   digit 个数      │  │ 符号 + 标志  │
    └─────────────────┘  └──────────────┘

低位 3 位的含义：

- ``0b00``: 正数 (``1 << 0``)
- ``0b01``: 零
- ``0b10``: 负数 (``2 << 0``)
- 第三位 ``0b100``: 小整数标记

.. mermaid::

    flowchart LR
        tag["lv_tag<br/>= 0x0002_XXXX"] --> ndigits["高位: ndigits = 2"]
        tag --> sign["低位: sign = 0b10 (负号)"]
        ndigits --> d0["ob_digit[0] = 低 30 位"]
        ndigits --> d1["ob_digit[1] = 高 30 位"]

数字的值计算公式：

.. code-block:: text

    value = (-1)^sign * Σ(ob_digit[i] * 2^(PyLong_SHIFT * i))

其中 ``PyLong_SHIFT`` 在 64 位系统上是 **30** （每个 digit 30 位），
在少数 32 位系统上是 15。这样每个 digit 能存约 10 亿级别的数值。

第二问：小整数的特殊优化
--------------------------

CPython 对小整数做了两个重要优化：

**1. 小整数池 (Small Integer Cache)**

启动时预分配 ``-5`` 到 ``257`` 的整数对象，永远复用：

.. code-block:: python

    >>> a = 256; b = 256
    >>> a is b   # True — 复用的
    >>> c = 258; d = 258
    >>> c is d   # False — 每次新建

这个范围的数值在 Python 代码中极其常用（列表索引、循环计数……），预分配避免了大量
堆分配开销。

**2. Compact 小整数**

当数值能用一个 digit 装下时（即绝对值 < ``2^30`` ），``lv_tag`` 的高位直接存数值本身，
不需要 ``ob_digit`` 数组。``_PyLong_IsCompact()`` 检测这种情况。

.. code-block:: c

    static inline Py_ssize_t
    _PyLong_CompactValue(const PyLongObject *op)
    {
        // sign = 1（正）, 0（零）, 或 -1（负）
        Py_ssize_t sign = 1 - (op->long_value.lv_tag & _PyLong_SIGN_MASK);
        // 直接读第一个 digit 作为值
        return sign * (Py_ssize_t)op->long_value.ob_digit[0];
    }

第三问：大整数运算——以加法为例
--------------------------------

当两个大整数相加时，CPython 的 ``long_add`` 会：

#. 比较两个数的长度（digit 个数）
#. 逐 digit 相加，处理进位
#. 如果结果长度超出预期，重新分配内存

.. code-block:: c

    // long_add 的核心路径：x_add
    static PyLongObject *
    x_add(PyLongObject *a, PyLongObject *b)
    {
        Py_ssize_t size_a = PyLong_NUM_BYTES(a);  // digit 个数
        Py_ssize_t size_b = PyLong_NUM_BYTES(b);
        PyLongObject *z;
        digit carry = 0;

        // 按较长的位数分配结果空间
        z = _PyLong_New(MAX(size_a, size_b) + 1);

        for (i = 0; i < size_b; ++i) {
            carry += a->long_value.ob_digit[i] + b->long_value.ob_digit[i];
            z->long_value.ob_digit[i] = carry & PyLong_MASK;
            carry >>= PyLong_SHIFT;
        }
        // 处理剩余高位...
        return z;
    }

这就是 Python 整数不会溢出的原因：**位数不够时就分配更多 digit** 。

第四问：小整数池的 C 层实现
----------------------------

CPython 在 ``_PyLong_Init`` 中初始化小整数池：

.. code-block:: c

    int _PyLong_Init(PyInterpreterState *interp)
    {
        for (Py_ssize_t i = 0; i < NSMALLNEGINTS + NSMALLPOSINTS; i++) {
            PyLongObject *v = _PyLong_New(1);
            v->long_value.ob_digit[0] = i - NSMALLNEGINTS;  // -5 到 257
            // 标记为 immortal，跳过引用计数操作
            _Py_SetImmortal(v);
            interp->small_ints[i] = v;
        }
    }

然后 ``PyLong_FromLong`` 检查是否是小整数范围，是就直接返回预分配对象：

.. code-block:: c

    PyObject * PyLong_FromLong(long ival)
    {
        if (IS_SMALL_INT(ival)) {
            // 直接从缓存取，避免堆分配
            return Py_NewRef(GET_SMALL_INT(ival));
        }
        // 否则新建一个大整数
        return _PyLong_FromLarge(ival);
    }

第五问：int 的运算在类型对象中如何注册？
----------------------------------------

``PyLong_Type`` 的 ``tp_as_number`` 字段指向 ``long_as_number`` 结构体：

.. code-block:: c

    static PyNumberMethods long_as_number = {
        .nb_add = long_add,         // +
        .nb_subtract = long_sub,    // -
        .nb_multiply = long_mul,    // *
        .nb_remainder = long_mod,   // %
        .nb_power = long_pow,       // **
        .nb_negative = long_neg,    // -x
        .nb_absolute = long_abs,    // abs()
        .nb_bool = long_bool,       // bool(x) — 非零即 True
        .nb_invert = long_invert,   // ~x
        .nb_lshift = long_lshift,   // <<
        .nb_rshift = long_rshift,   // >>
        .nb_and = long_and,         // &
        .nb_or = long_or,           // |
        .nb_xor = long_xor,         // ^
        .nb_int = long_int,         // int(x)
        .nb_index = long_index,     // __index__
    };

每个 ``nb_*`` 字段都是一个函数指针。所以 ``a + b`` 经过 ``BINARY_OP`` 字节码指令
分发到 ``PyLong_Type`` 的 ``tp_as_number->nb_add``，即 ``long_add`` 。

通过示例脚本验证
----------------

运行 :file:`examples/longobject_demo.py`：

.. code-block:: text

    --- 小整数池 ---
    256 的 id: 0x...
    256 的 id: 0x...（同一个）
    258 的 id: 0x...（不同）

    --- 大整数长度 ---
    2**1000 有 34 个 digit

    --- 整数运算 ---
    2**1000 + 2**1000 = 2**1001

    --- compact 检测 ---
    42: compact=True, value=42
    2**100: compact=False

小结
----

.. list-table::
   :header-rows: 1

   * - 特性
     - 实现方式
   * - 变长精度
     - ``ob_digit[]`` 数组，每个 30 位
   * - 小整数池
     - ``-5`` 到 ``257`` 预分配
   * - Compact 小整数
     - 单 digit，lv_tag 标记
   * - 符号表示
     - lv_tag 低 2 位
   * - 运算符注册
     - ``long_as_number`` 函数表

参考资料
--------

- :file:`Include/longintrepr.h` — ``PyLongObject`` 内部表示（digit / lv_tag）
- :file:`Objects/longobject.c` — 大整数运算实现
- `Knuth, The Art of Computer Programming, Vol. 2` — 多精度算术算法

