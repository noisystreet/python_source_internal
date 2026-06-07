指令特化 (Specialization) — 自适应优化
=============================================

CPython 3.11+ 引入了**自适应字节码指令 (Adaptive Instruction)**——指令在运行时
根据参数的实际类型，将自己替换为**特化版本** 。

从一道题开始
------------

.. code-block:: python

    for _ in range(1000):
        a + b      # 前几次是通用加法，之后变成整数加法特化

前几次执行 ``a + b`` 时，``BINARY_OP`` 是通用版本——它会检查 ``a`` 和 ``b`` 的类型，
分发到对应的 ``nb_add`` 。但如果 ``a`` 和 ``b`` 总是整数，CPython 会将这条指令
**原地替换** 为 ``BINARY_OP_ADD_INT``——不再检查类型，直接做整数加法。

.. mermaid::

    flowchart TD
        gen["BINARY_OP (通用)"] --> check{"计数器触发?"}
        check -->|"否"| execute_gen["执行通用加法"]
        execute_gen --> inc["计数器++"]
        check -->|"是"| specialize["_Py_Specialize_BinaryOp"]
        specialize -->|"int + int"| spec_int["BINARY_OP_ADD_INT"]
        specialize -->|"float + float"| spec_float["BINARY_OP_ADD_FLOAT"]
        specialize -->|"str + str"| spec_str["BINARY_OP_ADD_UNICODE"]
        specialize -->|"其他"| general["保持通用"]

第一问：自适应指令的机制
------------------------

每条自适应指令开头有一个**特化计数器** （存储在指令后的缓存槽中）：

.. code-block:: c

    // BINARY_OP 指令的前几条缓存
    // this_instr[0] = BINARY_OP
    // this_instr[1] = counter (16位计数器)
    // this_instr[2..5] = 4个缓存槽

    TARGET(BINARY_OP) {
        next_instr += 6;  // 指令本身 + 5个缓存槽

        uint16_t counter = read_u16(&this_instr[1].cache);

        // 检查计数器是否触发
        if (ADAPTIVE_COUNTER_TRIGGERS(counter)) {
            _Py_Specialize_BinaryOp(lhs, rhs, next_instr, oparg);
            DISPATCH_SAME_OPARG();
        }

        // 增加计数器
        ADVANCE_ADAPTIVE_COUNTER(this_instr[1].counter);

        // 通用加法实现
        PyObject *res = Py_BinaryOp(lhs_o, rhs_o, oparg);
        ...
    }

当计数器触发时，``_Py_Specialize_BinaryOp`` 检查操作数的实际类型，然后**重写
指令的第一个字**为特化后的操作码。

第二问：CALL 指令的特化
-----------------------

``CALL`` 指令的特化是最重要的，因为它直接影响函数调用的性能：

.. code-block:: c

    void _Py_Specialize_Call(_PyStackRef callable, _Py_CODEUNIT *instr, int nargs)
    {
        PyObject *callable_obj = ...;

        if (PyCFunction_CheckExact(callable)) {
            // 内置 C 函数 → CALL_BUILTIN_FAST
            specialize_c_call(callable, instr, nargs);
        }
        else if (PyFunction_Check(callable)) {
            // Python 函数 → CALL_PY_EXACT_ARGS
            specialize_py_call(callable, instr, nargs, false);
        }
        else if (PyType_Check(callable)) {
            // 类调用 → CALL_ALLOC_AND_ENTER_INIT
            specialize_class_call(callable, instr, nargs);
        }
        else if (PyMethod_Check(callable)) {
            // 方法调用 → CALL_BOUND_METHOD_EXACT_ARGS
            ...
        }
        else {
            // 其他 → CALL_NON_PY_GENERAL
            specialize(instr, CALL_NON_PY_GENERAL);
        }
    }

特化后的 CALL 指令：

.. list-table::
   :header-rows: 1

   * - 特化指令
     - 适用场景
     - 优势
   * - ``CALL_PY_EXACT_ARGS``
     - 调用纯 Python 函数
     - 跳过方法展开、直接创建帧
   * - ``CALL_BUILTIN_FAST``
     - 调用内置 C 函数（如 ``len()`` ）
     - 直接调用 ``vectorcall``，零检查
   * - ``CALL_BOUND_METHOD_EXACT_ARGS``
     - 调用绑定的方法
     - 简化 self 绑定逻辑
   * - ``CALL_ALLOC_AND_ENTER_INIT``
     - ``MyClass()``
     - 合并分配和初始化
   * - ``CALL_NON_PY_GENERAL``
     - 其他可调用对象（带 ``__call__`` 的类实例）
     - 跳过类型检查

第三问：二进制运算的特化
------------------------

``BINARY_OP`` 的特化根据操作数的运行时类型：

.. code-block:: c

    void _Py_Specialize_BinaryOp(PyObject *lhs, PyObject *rhs,
                                  _Py_CODEUNIT *instr, int oparg)
    {
        if (oparg != NB_ADD) {
            // 目前只特化加法
            SPECIALIZATION_FAIL(BINARY_OP, SPEC_FAIL_OPARG);
            goto fail;
        }
        if (PyLong_CheckExact(lhs) && PyLong_CheckExact(rhs)) {
            specialize(instr, BINARY_OP_ADD_INT);
        }
        else if (PyFloat_CheckExact(lhs) && Py_Float_CheckExact(rhs)) {
            specialize(instr, BINARY_OP_ADD_FLOAT);
        }
        else if (PyUnicode_CheckExact(lhs) && PyUnicode_CheckExact(rhs)) {
            specialize(instr, BINARY_OP_ADD_UNICODE);
        }
        else {
            SPECIALIZATION_FAIL(...);
            goto fail;
        }
    }

特化后的指令直接进行底层运算，不再经过 ``Py_BinaryOp`` 的类型分发：

.. code-block:: c

    TARGET(BINARY_OP_ADD_INT) {
        PyObject *lhs_o = ...;
        PyObject *rhs_o = ...;
        // 直接调用 long_add，不需要检查类型
        PyObject *res = long_add(lhs_o, rhs_o);
        stack_pointer[-2] = PyStackRef_FromPyObjectSteal(res);
        stack_pointer--;
        DISPATCH();
    }

第四问：反特化 (Unspecialization)
----------------------------------

如果特化版本发现类型不匹配（例如之前一直是 ``int + int``，但突然来了个 ``str + int`` ），
它会**反特化**——把指令恢复为通用版本：

.. code-block:: c

    TARGET(BINARY_OP_ADD_INT) {
        PyObject *lhs_o = ...;
        PyObject *rhs_o = ...;

        if (!PyLong_CheckExact(lhs_o) || !PyLong_CheckExact(rhs_o)) {
            // 类型不匹配！反特化
            _Py_Specialize_BinaryOp(lhs_o, rhs_o, this_instr, NB_ADD);
            // 重新执行（这次走通用路径）
            DISPATCH_SAME_OPARG();
        }

        // 正常的整数加法
        ...
    }

反特化时，CPython 不会恢复到原来的 ``BINARY_OP``，而是**再次调用** ``_Py_Specialize_*``
重新根据当前类型选择特化版本。这样可以跟踪类型变化的模式。

第五问：LOAD_ATTR 的特化
-------------------------

属性访问（``obj.attr`` ）也是特化的重要目标：

.. code-block:: c

    void _Py_Specialize_LoadAttr(PyObject *owner, _Py_CODEUNIT *instr, PyObject *name)
    {
        PyTypeObject *type = Py_TYPE(owner);

        if (type->tp_getattro == PyObject_GenericGetAttr) {
            // 通用属性访问 → 查找描述符或实例字典
            // 进一步特化...
            if (type->tp_flags & Py_TPFLAGS_MANAGED_DICT) {
                specialize(instr, LOAD_ATTR_MANAGED_DICT);
            }
        }
        // ...
    }

特化后的 ``LOAD_ATTR`` 可以变成：

- ``LOAD_ATTR_MANAGED_DICT`` ：直接读实例字典
- ``LOAD_ATTR_INSTANCE_VALUE`` ：直接从类型插槽中读
- ``LOAD_ATTR_WITH_HINT`` ：带缓存提示的属性访问
- ``LOAD_ATTR_SLOT`` ：直接读 ``__slots__`` 属性

通过示例脚本验证
----------------

运行 :file:`examples/specialize_demo.py`：

.. code-block:: text

    --- 第一次调用（通用） ---
    len([1,2]): 通用 CALL

    --- 多次调用后（特化） ---
    len([1,2]): CALL_BUILTIN_FAST

    --- 加法特化 ---
    a + b: int + int → BINARY_OP_ADD_INT
    a + b: float + float → BINARY_OP_ADD_FLOAT

    --- 属性访问特化 ---
    obj.attr: LOAD_ATTR 特化

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 什么是特化？
     - 运行时根据类型将通用指令替换为专用版本
   * - 什么时候触发特化？
     - 自适应计数器达到阈值
   * - 特化能撤销吗？
     - 可以（反特化），类型变化时恢复通用版本
   * - CALL 有哪些特化版本？
     - CALL_PY_EXACT_ARGS / CALL_BUILTIN_FAST / CALL_BOUND_METHOD 等
   * - BINARY_OP 有哪些特化版本？
     - BINARY_OP_ADD_INT / ADD_FLOAT / ADD_UNICODE
   * - LOAD_ATTR 有哪些特化版本？
     - 字典查找 / 类型插槽 / __slots__ 等

参考资料
--------

- :pep:`659` — 自适应特化
- :file:`Python/ceval.c` — 特化缓存的维护与失效
- :file:`Python/specialize.c` — 特化逻辑实现
- `GH-28676 <https://github.com/python/cpython/issues/28676>`__ — 内联缓存设计

