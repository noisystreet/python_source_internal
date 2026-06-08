函数与代码对象 — def 背后的结构
==================================

在 Python 里定义一个函数很简单：

.. code-block:: python

    def add(a, b):
        return a + b

但这一行代码在 CPython 中创建了**两个对象** ：

- 一个 ``PyFunctionObject`` （函数对象）—— 就是 ``add``
- 一个 ``PyCodeObject`` （代码对象）—— 藏在 ``add.__code__`` 里

这一节我们就拆开这两个结构体，看看到底存了什么。

从一道题开始
------------

试试这段代码：

.. code-block:: python

    def add(a, b):
        return a + b

    print(type(add))        # <class 'function'>
    print(type(add.__code__))  # <class 'code'>

函数是对象，函数的"代码"也是对象。但为什么需要两个对象？

**因为它们的职责完全不同：**

- ``PyCodeObject`` 是**静态的** ：存着编译后的字节码、常量、变量名——一旦编译好就不再改变
- ``PyFunctionObject`` 是**动态的** ：存着函数名、默认参数、闭包、全局命名空间——每次 ``def`` 执行时创建

.. mermaid::

    flowchart LR
        def_stmt["执行 def add(a, b):\nreturn a + b"] --> compile["编译器编译函数体"]
        compile --> code_obj["PyCodeObject\n（静态字节码）"]
        code_obj --> func_obj["PyFunctionObject\n（动态上下文）"]
        func_obj --> add["add(a, b)"]
        add -->|".__code__"| code_obj

第一问：PyFunctionObject 里有什么？
-----------------------------------

先看 C 结构体：

.. code-block:: c

    typedef struct {
        PyObject_HEAD
        PyObject *func_globals;     // 函数定义所在的全局命名空间
        PyObject *func_builtins;    // 内置命名空间
        PyObject *func_name;        // 函数名（__name__）
        PyObject *func_qualname;    // 限定名（__qualname__）
        PyObject *func_code;        // 代码对象（__code__）
        PyObject *func_defaults;    // 默认参数元组或 NULL
        PyObject *func_kwdefaults;  // 关键字默认参数字典或 NULL
        PyObject *func_closure;     // 闭包绑定的 cell 对象元组或 NULL
        PyObject *func_doc;         // __doc__
        PyObject *func_dict;        // __dict__（任意属性字典）
        PyObject *func_weakreflist; // 弱引用链表
        PyObject *func_module;      // __module__
        PyObject *func_annotations; // 类型注解
        vectorcallfunc vectorcall;  // 快速调用入口
        uint32_t func_version;      // 版本号（给特化器用）
    } PyFunctionObject;

核心字段可以分为几组：

**命名空间（决定变量在哪里找）**
  - ``func_globals`` ：``def`` 语句所在位置的 ``globals()``
  - ``func_builtins`` ：内置函数（``print`` 、``len`` 等）

**代码**
  - ``func_code`` ：指向 ``PyCodeObject``

**参数**
  - ``func_defaults`` ：``def add(a, b=1)`` 中的 ``(1,)``
  - ``func_kwdefaults`` ：``def f(**kw)`` 中的关键字默认值

**闭包**
  - ``func_closure`` ：嵌套函数捕获的外部变量

**调用优化**
  - ``vectorcall`` ：一个精心优化的函数调用入口，比传统的 ``tp_call`` 更快

.. tip::

   你可以手动查看函数的 ``__code__`` 、``__globals__`` 、``__closure__`` 等属性。
   下一节的示例脚本会演示如何在 Python 层观察这些字段。

第二问：PyCodeObject 里有什么？
-------------------------------

代码对象的结构要复杂得多。它也是一个 ``PyVarObject`` （变长对象），因为末尾的字节码数组长度可变。

.. code-block:: c

    struct PyCodeObject {
        PyObject_VAR_HEAD           // 可变长头部

        // ★ 执行引擎最常访问的字段（放在最前面，cache line 友好）
        PyObject *co_consts;        // 常量元组（如 42, "hello"）
        PyObject *co_names;         // 名字元组（如 "print", "add"）
        PyObject *co_exceptiontable;// 异常处理表

        int co_flags;               // 特性标志
        int co_argcount;            // 位置参数个数
        int co_posonlyargcount;     // 仅限位置参数个数
        int co_kwonlyargcount;      // 仅限关键字参数个数
        int co_stacksize;           // 评估栈所需大小
        int co_firstlineno;         // 源代码起始行号

        int co_nlocalsplus;         // 局部+cell+free 变量总数
        int co_framesize;           // 帧大小（字长）
        int co_nlocals;             // 局部变量数
        int co_ncellvars;           // cell 变量数
        int co_nfreevars;           // free 变量数
        uint32_t co_version;        // 版本号

        PyObject *co_localsplusnames; // 变量名元组
        PyObject *co_localspluskinds; // 变量类型编码
        PyObject *co_filename;      // 源文件名
        PyObject *co_name;          // 函数名
        PyObject *co_qualname;      // 限定名
        PyObject *co_linetable;     // 行号表（字节码偏移 → 行号）
        ...

        // 末尾：变长字节码数组
        char co_code_adaptive[...]; // 自适应字节码
    };

.. mermaid::

    graph TD
        subgraph PyCodeObject
            co_consts["co_consts<br/>(42, 'hello', ...)"]
            co_names["co_names<br/>('print', 'add', ...)"]
            co_varnames["co_localsplusnames<br/>('a', 'b')"]
            co_filename["co_filename<br/>('example.py')"]
            co_code["co_code_adaptive<br/>(字节码指令数组)"]
        end

最有意思的字段在 ``co_flags`` 里。它告诉你这个函数的性质：

.. code-block:: c

    #define CO_OPTIMIZED     0x0001  // 使用 fastlocals（大部分函数都是）
    #define CO_NEWLOCALS     0x0002  // 有局部变量空间
    #define CO_VARARGS       0x0004  // 有 *args
    #define CO_VARKEYWORDS   0x0008  // 有 **kwargs
    #define CO_NESTED        0x0010  // 是嵌套函数
    #define CO_GENERATOR     0x0020  // 是生成器函数
    #define CO_COROUTINE     0x0080  // async def
    #define CO_ASYNC_GENERATOR 0x0200 // async generator
    #define CO_METHOD        0x8000000 // 定义在类作用域中

第三问：def 执行时发生了什么？
------------------------------

当你调用 ``def add(a, b): return a + b`` 时，CPython 实际上做了这些事：

.. mermaid::

    flowchart TD
        A["MAKE_FUNCTION 字节码指令"] --> B["从 co_consts 取出代码对象"]
        B --> C["PyFunction_New(code, globals)"]
        C --> D["设置 func_name = co.co_name"]
        D --> E["设置 func_defaults（如果有）"]
        E --> F["设置 func_closure（如果有）"]
        F --> G["将函数对象赋值给变量 add"]

这个过程核心是 ``MAKE_FUNCTION`` 字节码指令。它从常量池中取出代码对象，然后包装成一个函数对象。

.. note::

   **代码对象是在编译时创建的**——``def`` 所在模块被 ``import`` 或执行时，
   整个模块的源代码被编译成字节码，每个函数体对应一个 ``PyCodeObject`` 。
   然后执行到 ``MAKE_FUNCTION`` 时，才用代码对象创建函数对象。

这就是为什么**一个 ``def`` 语句同时涉及编译器和运行时** 。

第四问：函数是怎么被调用的？
----------------------------

当你写 ``add(1, 2)`` 时：

#. CPython 执行 ``CALL`` 字节码指令
#. 它找到 ``add`` 这个 ``PyFunctionObject``
#. 检查 ``vectorcall`` 字段（优选的快速路径）
#. 用参数创建一个帧 (frame)
#. 在帧上执行代码对象的字节码

.. mermaid::

    flowchart LR
        call["add(1, 2)"] -->|"CALL 指令"| func["PyFunctionObject"]
        func -->|"vectorcall"| frame["创建帧 (Frame)"]
        frame -->|"执行字节码"| result["返回结果 3"]

``vectorcall`` 是 CPython 3.12+ 中函数调用的核心协议。它是一个经过高度优化的
函数指针，可以直接被 ``CALL`` 指令调用，绕过 ``tp_call`` 的通用分发路径。

.. code-block:: c

    // funcobject.c 中 PyFunctionObject 的 vectorcall 设置
    PyFunctionObject *op = ...;
    op->vectorcall = _PyFunction_Vectorcall;
    // 后续 CALL 指令直接调用 op->vectorcall(func, args, nargs, kwnames)

第五问：闭包是怎么实现的？
--------------------------

闭包（closure）是嵌套函数捕获外部变量的机制。CPython 通过 **cell 对象** 实现。

.. code-block:: python

    def outer(x):
        def inner(y):
            return x + y
        return inner

    f = outer(10)
    print(f(5))  # 15

这里发生了什么？

#. ``outer(10)`` 执行时，参数 ``x = 10`` 是一个局部变量
#. 定义 ``inner`` 时，发现它引用了 ``x``——但 ``x`` 不是 ``inner`` 的参数或局部变量
#. 编译器标记 ``x`` 为 **cell 变量**，把 ``x`` 的值存入一个 **cell 对象**
#. ``inner`` 的 ``func_closure`` 字段指向包含 ``x`` 的 cell 元组

.. mermaid::

    flowchart LR
        outer_frame["outer 的帧<br/>local x = 10"] --> cell["cell 对象<br/>x = 10"]
        cell --> inner_closure["inner.func_closure<br/>(<cell at 0x...>)"]
        inner_func["inner"] --> inner_closure

在 C 层，这对应：

.. code-block:: c

    // 当 inner 访问 x 时，实际执行的是：
    PyObject *val = PyCell_GET(inner->func_closure[0]);
    // val = 10

Cell 对象本身就是一个简单的结构体：

.. code-block:: c

    typedef struct {
        PyObject_HEAD
        PyObject *ob_ref;  // 引用的实际对象
    } PyCellObject;

当 ``outer`` 退出后，虽然 ``x`` 作为局部变量已经消失，但 cell 对象中保留了 ``x`` 的值引用，
所以 ``inner`` 仍然可以访问它。

第六问：默认参数和注解存在哪里？
--------------------------------

默认参数是最容易让人困惑的 Python 特性之一：

.. code-block:: python

    def f(x, lst=[]):
        lst.append(x)
        return lst

    print(f(1))  # [1]
    print(f(2))  # [1, 2] ← 因为 lst 是同一个对象！

默认参数存储在 ``func_defaults`` 中，这是一个元组。**默认参数在函数定义时求值一次**，
之后每次调用都复用同一个对象。这就是为什么可变默认参数会累积值。

.. code-block:: c

    // 执行 def 时
    func->func_defaults = PyTuple_Pack(1, empty_list);
    // 这个 empty_list 被所有调用共享

注解（annotations）则存储在 ``func_annotations`` 中。默认惰性求值（Python 3.11+）：

.. code-block:: python

    def f(x: int) -> str:
        return str(x)

    # f.__annotations__ == {'x': int, 'return': str}

在 C 层，这是在编译时就准备好的字典，直接赋值给 ``func_annotations`` 。

通过示例脚本验证
----------------

运行 :file:`examples/function_code_demo.py`：

.. code-block:: text

    --- add 函数的信息 ---
    add.__name__ = add
    add.__code__ 地址 = 0x...

    --- 代码对象字段 ---
    co_argcount = 2
    co_nlocals = 2
    co_varnames = ('a', 'b')
    co_consts = (None,)
    co_names = ()
    co_flags = 99 (0b0001100011)
      → CO_OPTIMIZED, CO_NEWLOCALS, ...

    --- 闭包验证 ---
    outer(10) 返回 inner(5) = 15
    inner.__closure__ = (<cell at 0x...: int object at 0x...>,)

    --- 默认参数陷阱 ---
    第一次调用: [1]
    第二次调用: [1, 2]  ← 同一个列表！

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 函数对象和代码对象有什么区别？
     - 代码对象存静态字节码；函数对象存动态上下文
   * - 代码对象有哪些核心字段？
     - co_consts（常量）、co_names（名字）、co_code（字节码）、co_flags（标志）
   * - def 执行时 CPython 做了什么？
     - 从常量池取代码对象 → 创建函数对象 → 设置默认参数/闭包
   * - 函数调用如何工作？
     - CALL 指令通过 vectorcall 协议创建帧并执行字节码
   * - 闭包怎么实现？
     - cell 对象在函数返回后持有捕获变量的引用
   * - 默认参数为什么是"陷阱"？
     - 默认参数在 def 时求值一次，存在 func_defaults 中共享

下一步
------

理解了函数和代码对象后，我们来看**迭代器与生成器协议**——Python 中 ``for`` 循环和 ``yield`` 的底层实现。

参考资料
--------

- :file:`Objects/funcobject.c` — PyFunctionObject 实现
- :file:`Objects/codeobject.c` — PyCodeObject 实现
- :pep:`302` — 新导入钩子
