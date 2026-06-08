.. _ceval-calls:

调用约定与栈帧 — PyObject_Vectorcall 协议
===============================================

.. epigraph::

   "A journey of a thousand miles begins with a single step."

   -- Lao Tzu, Tao Te Ching


上一节我们看到了 ``CALL`` 指令。这一节深入函数调用的核心——**Vectorcall 协议** ，
以及 **栈帧的创建与切换** 。

从一道题开始
------------

.. code-block:: python

    def f(a, b, c):
        return a + b + c

    f(1, 2, 3)  # 调用时发生了什么？

当 CPython 执行 ``f(1, 2, 3)`` 时：

#. 参数 ``1, 2, 3`` 被压入评估栈
#. 函数对象 ``f`` 也在栈上
#. ``CALL`` 指令从栈上读取函数和参数
#. 通过 ``vectorcall`` 协议调用函数
#. 为 ``f`` 创建一个新的 ``_PyInterpreterFrame``
#. 在新帧上继续执行 ``f`` 的字节码
#. ``f`` 返回后，销毁帧，恢复调用者

第一问：Vectorcall 协议是什么？
-------------------------------

Vectorcall（PEP 590）是 CPython 3.9+ 引入的统一函数调用协议：

.. code-block:: c

    // vectorcall 函数指针类型
    typedef PyObject *(*vectorcallfunc)(
        PyObject *callable,     // 被调用的对象
        PyObject *const *args,  // 参数数组
        size_t nargsf,          // 参数个数（含标志位）
        PyObject *kwnames       // 关键字参数名元组或 NULL
    );

所有可调用对象（函数、方法、类、实现了 ``__call__`` 的对象）都有一个
``vectorcall`` 函数指针：

.. code-block:: c

    // PyFunctionObject 中有 vectorcall 字段
    typedef struct {
        PyObject_HEAD
        // ... 其他字段 ...
        vectorcallfunc vectorcall;  // ★ 指向调用入口
        uint32_t func_version;
    } PyFunctionObject;

    // PyTypeObject 中也有
    typedef struct _typeobject {
        // ...
        vectorcallfunc tp_vectorcall;
    };

.. mermaid::

    flowchart TD
        call["CALL 指令"] --> lookup["取 callable->vectorcall"]
        lookup -->|"有 vectorcall"| direct["直接调用 vectorcall(func, args, nargs, kwnames)"]
        lookup -->|"无 vectorcall"| fallback["回退到 tp_call<br/>(PyObject_Call 传统路径)"]
        direct --> result["返回结果"]
        fallback --> result

第二问：参数是如何传递的？
--------------------------

Vectorcall 的参数传递方式：

.. code-block:: text

    栈布局示例：f(1, 2, 3, k=4)

    低地址                    高地址
    ┌──────┬──────┬──────┬──────┬──────┐
    │ func │ self │ arg1 │ arg2 │ arg3 │  ← 评估栈
    │      │ =NULL│ =1   │ =2   │ =3   │
    └───┬──┴──┬───┴──────┴──────┴──────┘
        │     └─ 传给 vectorcall 的 args
        └─────── callable

    kwnames = ("k",)  ← 关键字参数名元组

``nargsf`` 的低位是参数个数，高位含标志位：

.. code-block:: c

    size_t nargs = nargsf & ~VECTORCALL_ARG_FLAGS;
    // 判断是否有关键字参数
    bool has_kwargs = nargsf & PY_VECTORCALL_ARGUMENT_MASK;

``args`` 数组的第一个元素可能是 ``self`` （方法调用时），也可能直接是参数。

第三问：函数的帧是如何创建的？
-------------------------------

当 ``CALL`` 指令发现调用的是 Python 函数（不是 C 扩展函数）时，
通过 ``_PyFunction_Vectorcall`` 创建新帧：

.. code-block:: c

    // Objects/call.c 中的简化流程
    PyObject *
    _PyFunction_Vectorcall(PyObject *func, PyObject *const *args,
                            size_t nargsf, PyObject *kwnames)
    {
        PyFunctionObject *f = (PyFunctionObject *)func;
        PyCodeObject *code = (PyCodeObject *)f->func_code;

        // 1. 创建 _PyInterpreterFrame 并推入帧栈
        _PyInterpreterFrame *frame = _PyEvalFramePushAndInit(
            tstate, func, code, args, nargsf, kwnames);

        // 2. 执行字节码
        PyObject *result = _PyEval_EvalFrame(tstate, frame, 0);

        // 3. 返回结果
        return result;
    }

``_PyEvalFramePushAndInit`` 做了关键工作：

#. 从 ``co_framesize`` 知道帧需要多大空间
#. 在堆上分配 ``_PyInterpreterFrame`` （或从自由列表复用）
#. 设置 ``frame->previous = tstate->current_frame`` （形成帧链）
#. 将参数从调用者的栈拷贝到新帧的 ``localsplus[]``
#. 设置 ``instr_ptr`` 指向函数的第一条指令（ ``RESUME`` ）
#. 设置 ``tstate->current_frame = frame`` （切换到新帧）

.. mermaid::

    flowchart LR
        caller_frame["调用者的帧<br/>_PyInterpreterFrame"] -->|"previous"| callee_frame["被调用者的帧<br/>_PyInterpreterFrame"]
        callee_frame -->|"执行完毕后"| ret["恢复调用者的帧"]
        subgraph Stack["帧链"]
            f1["frame1 (main)"]
            f2["frame2 (f)"]
            f3["frame3 (g)"]
        end
        f1 --> f2 --> f3

第四问：关键字参数怎么处理的？
------------------------------

关键字参数处理在 ``_PyEvalFramePushAndInit`` 中：

.. code-block:: c

    // 简化后的关键字参数处理
    // kwnames 是一个元组，存着所有关键字参数的名字
    for (Py_ssize_t i = 0; i < PyTuple_GET_SIZE(kwnames); i++) {
        PyObject *key = PyTuple_GET_ITEM(kwnames, i);
        PyObject *value = args[nargs + i];  // 关键字参数值在 args 末尾

        // 在 co_varnames 中查找参数名索引
        int idx = _PyCode_Lookup(code, key);
        if (idx >= 0) {
            localsplus[idx] = value;  // 填入局部变量槽位
        } else {
            // 不在参数列表中 → 放入 **kwargs 字典（如果有）
        }
    }

第五问：方法的调用（self 绑定）
-------------------------------

当调用 ``obj.method()`` 时，方法已经是一个 ``PyMethodObject`` （bound method）：

.. code-block:: c

    // CALL 指令中的方法展开
    if (PyStackRef_TYPE(callable) == &PyMethod_Type
        && PyStackRef_IsNull(self_or_null)) {

        PyMethodObject *method = (PyMethodObject *)callable_o;
        // 解开 bound method：取出函数和 self
        PyObject *func = method->im_func;
        PyObject *self = method->im_self;

        // 用 func 替换 callable，self 插入到 args 最前面
        callable = func;
        // args[-1] = self（使得 self 在参数列表中排第一）
    }

这就是为什么 ``obj.method(args)`` 在 C 层等价于 ``Class.method(obj, args)`` 。

第六问：生成器函数的调用差异
-----------------------------

生成器函数也是通过 ``_PyFunction_Vectorcall`` 调用的。关键区别在于：

.. code-block:: c

    // 生成器函数返回的是生成器对象，而不是执行函数体
    if (code->co_flags & CO_GENERATOR) {
        return PyGen_NewWithQualName(frame, name, qualname);
    }

    // 普通函数直接执行
    return _PyEval_EvalFrame(tstate, frame, 0);

生成器调用 **不执行函数体**——它只是创建帧并冻结在 ``FRAME_CREATED`` 状态，
然后返回 ``PyGenObject`` 。帧的执行延迟到 ``next(gen)`` 被调用时。

通过示例脚本验证
----------------

运行 :file:`examples/calls_demo.py`：

.. code-block:: text

    --- vectorcall 参数布局 ---
    f(1, 2, 3): nargs=3, 无关键字参数

    --- 调用链的帧深度 ---
    a() → b() → c(): 帧深度 = 3

    --- 递归的帧开销 ---
    factorial(10): 10 个帧

    --- 方法调用 vs 函数调用 ---
    obj.method() → 内部变成 Class.method(obj)

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - Vectorcall 协议是什么？
     - ``vectorcallfunc`` 函数指针，统一所有可调用对象的调用入口
   * - 参数如何传递？
     - ``args`` 数组 + ``nargsf`` 位标志 + ``kwnames`` 元组
   * - 帧如何创建？
     - ``_PyEvalFramePushAndInit`` 分配帧、初始化局部变量
   * - 关键字参数怎么处理？
     - 按名字在 ``co_varnames`` 中查找索引，填入局部变量
   * - 方法的 self 怎么绑定？
     - ``PyMethodObject`` 展开，self 插入参数列表首位
   * - 生成器调用有何不同？
     - 只创建帧不执行，立即返回生成器对象

参考资料
--------

- :ref:`ceval-loop` — 解释循环与帧管理
- :ref:`objects-func-code` — 函数对象与代码对象
- :file:`Python/ceval.c` — 调用实现
- :pep:`590` — Vectorcall
