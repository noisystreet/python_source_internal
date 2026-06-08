.. _ceval-bytecodes:

核心字节码指令分析
=====================

.. epigraph::

   "Every program is a function of its input and its state."

   -- Simson Garfinkel


上一节我们看了解释循环的整体结构。这一节来拆解**具体指令的实现**——CPython 300+
字节码指令是如何在 C 层实现的，以及 3.14 中的超指令（superinstruction）优化。

从一道题开始
------------

.. code-block:: python

    a = 1       # LOAD_CONST + STORE_FAST
    b = a + 2   # LOAD_FAST + LOAD_CONST + BINARY_OP + STORE_FAST
    c = a + b   # LOAD_FAST_LOAD_FAST + BINARY_OP + STORE_FAST

注意第三行：CPython 3.14 将 ``LOAD_FAST a; LOAD_FAST b`` 合并为一条
``LOAD_FAST_LOAD_FAST`` 指令——这叫**超指令 (superinstruction)** 优化。

.. mermaid::

    flowchart LR
        subgraph Before["3.13 及之前"]
            i1["LOAD_FAST a<br/>(1 个字)"] --> i2["LOAD_FAST b<br/>(1 个字)"]
        end
        subgraph After["3.14 优化"]
            super["LOAD_FAST_LOAD_FAST a, b<br/>(1 个字)"]
        end

第一问：字节码指令的分类
--------------------------

CPython 的字节码指令可以分成几个功能组。以下是每组的核心指令：

**1. 加载/存储 (Load/Store)**
  操作局部变量和常量：

  .. list-table::
     :header-rows: 1

     * - 指令
       - C 层操作
       - 作用
     * - ``LOAD_FAST``
       - ``stack_pointer[0] = GETLOCAL(oparg); sp++``
       - 将局部变量压入栈
     * - ``LOAD_FAST_LOAD_FAST``
       - 一次加载两个局部变量（超指令）
       - 合并两条 ``LOAD_FAST``
     * - ``LOAD_CONST``
       - ``stack_pointer[0] = consts[oparg]; sp++``
       - 将常量压入栈
     * - ``STORE_FAST``
       - ``GETLOCAL(oparg) = stack_pointer[-1]; sp--``
       - 将栈顶值存入局部变量
     * - ``STORE_FAST_LOAD_FAST``
       - 先存一个再加载另一个（超指令）
       - 优化连续的 ``STORE_FAST; LOAD_FAST``

**2. 运算 (Binary Operations)**
  数学和逻辑运算：

  .. list-table::
     :header-rows: 1

     * - 指令
       - C 层操作
       - 作用
     * - ``BINARY_OP``
       - ``res = Py_BinaryOp(lhs, rhs, oparg)``
       - 通用二元运算（``+`` 、``-`` 、``*`` 等）
     * - ``BINARY_OP_ADD_INT``
       - ``res = lhs + rhs`` （特化版本）
       - 整数加法特化
     * - ``BINARY_OP_ADD_FLOAT``
       - ``res = lhs + rhs`` （特化版本）
       - 浮点数加法特化

  通用 ``BINARY_OP`` 指令在开头检查特化计数器，如果触发则调用
  ``_Py_Specialize_BinaryOp``，将指令替换为特化版本（如 ``BINARY_OP_ADD_INT`` ）。

**3. 函数调用 (Call)**

  .. list-table::
     :header-rows: 1

     * - 指令
       - C 层操作
       - 作用
     * - ``CALL``
       - ``oparg`` 指定参数个数
       - 通用函数调用
     * - ``CALL_BOUND_METHOD_EXACT_ARGS``
       - 直接调用绑定的方法
       - 方法调用特化
     * - ``CALL_BUILTIN_FAST``
       - ``builtin_func(args)``
       - 内置函数调用特化
     * - ``CALL_PY_EXACT_ARGS``
       - ``_PyEval_EvalFrameDefault(tstate, frame, 0)``
       - 纯 Python 函数调用特化

**4. 流程控制 (Control Flow)**

  .. list-table::
     :header-rows: 1

     * - 指令
       - C 层操作
       - 作用
     * - ``JUMP_FORWARD`` / ``JUMP_BACKWARD``
       - ``next_instr += offset``
       - 无条件跳转
     * - ``POP_JUMP_IF_TRUE`` / ``POP_JUMP_IF_FALSE``
       - 栈顶决定跳转
       - 条件跳转
     * - ``RETURN_VALUE``
       - 弹出返回值，恢复调用者帧
       - 从函数返回
     * - ``RESUME`` / ``RESUME_CHECK``
       - 检查生成器/异常恢复
       - 函数入口

第二问：LOAD_FAST — 最常用的指令
----------------------------------

``LOAD_FAST`` 是 CPython 中最常见的指令（通常占所有执行指令的 15-20%）：

.. code-block:: c

    // generated_cases.c.h
    TARGET(LOAD_FAST) {
        next_instr += 1;
        _PyStackRef value;

        // 从局部变量数组读取（oparg 是变量索引）
        assert(!PyStackRef_IsNull(GETLOCAL(oparg)));
        value = PyStackRef_DUP(GETLOCAL(oparg));

        // 压入评估栈
        stack_pointer[0] = value;
        stack_pointer += 1;

        DISPATCH();
    }

关键点：

- 通过 ``oparg`` 直接在 ``localsplus[]`` 数组中索引——**O(1) 时间**
- ``PyStackRef_DUP`` 复制引用（引用计数优化）
- 整个指令只有**几条 C 语句，几个 CPU 周期**

第三问：STORE_FAST — 写回局部变量
----------------------------------

.. code-block:: c

    TARGET(STORE_FAST) {
        next_instr += 1;
        _PyStackRef value;

        // 从栈顶取值
        value = stack_pointer[-1];

        // 保存旧值并写新值
        _PyStackRef tmp = GETLOCAL(oparg);
        GETLOCAL(oparg) = value;
        stack_pointer += -1;

        // 释放旧值的引用
        PyStackRef_XCLOSE(tmp);

        DISPATCH();
    }

注意 ``PyStackRef_XCLOSE(tmp)``——旧值可能引用计数归零，触发析构。
这就是为什么 ``x = something_new`` 可能回收 ``x`` 原来指向的对象。

第四问：CALL — 函数调用的核心
-------------------------------

``CALL`` 指令是所有函数调用的入口。它的结构比加载/存储复杂得多：

.. code-block:: c

    TARGET(CALL) {
        // 每条 CALL 指令占 4 个字（含 3 个缓存槽）
        next_instr += 4;
        _Py_CODEUNIT *this_instr = next_instr - 4;

        // 从评估栈获取：callable, self_or_null, args[]
        self_or_null = stack_pointer[-1 - oparg];
        callable = stack_pointer[-2 - oparg];

        // 特化检查
        uint16_t counter = read_u16(&this_instr[1].cache);
        if (ADAPTIVE_COUNTER_TRIGGERS(counter)) {
            _Py_Specialize_Call(callable, next_instr, oparg + ...);
            DISPATCH_SAME_OPARG();
        }

        // 展开方法调用（如果有 self）
        if (type(callable) == &PyMethod_Type && self_or_null == NULL) {
            callable = ((PyMethodObject *)callable)->im_func;
            self_or_null = ((PyMethodObject *)callable)->im_self;
        }

        // 调用函数
        res = PyObject_Vectorcall(callable, args, nargs, kwnames);

        // 清理栈并压入返回值
        stack_pointer -= nargs + 2;
        stack_pointer[0] = res;
        stack_pointer += 1;

        DISPATCH();
    }

特化机制使得 ``CALL`` 指令可以变成 ``CALL_PY_EXACT_ARGS`` （直接创建帧执行）、
``CALL_BUILTIN_FAST`` （直接调用 C 函数）等，大幅提升性能。

第五问：超指令 (Superinstruction) 优化
---------------------------------------

CPython 3.14 引入了超指令——**将两条频繁连续出现的字节码合并为一条** 。

最常见的就是 ``LOAD_FAST_LOAD_FAST`` ：

.. code-block:: c

    TARGET(LOAD_FAST_LOAD_FAST) {
        next_instr += 1;
        // oparg 编码了两个变量索引
        // 高 8 位 = 第一个变量，低 8 位 = 第二个变量
        uint16_t idx1 = oparg >> 8;
        uint16_t idx2 = oparg & 0xFF;

        stack_pointer[0] = PyStackRef_DUP(GETLOCAL(idx1));
        stack_pointer[1] = PyStackRef_DUP(GETLOCAL(idx2));
        stack_pointer += 2;

        DISPATCH();
    }

此外还有：

- ``STORE_FAST_LOAD_FAST`` ：先存一个变量，再加载另一个
- ``STORE_FAST_STORE_FAST`` ：连续存两个变量
- ``LOAD_FAST_BORROW_LOAD_FAST_BORROW`` ：借用引用加载（免 INCREF）

这些超指令**减少了指令分发的次数和字节码占用空间** 。

第六问：RETURN_VALUE — 函数返回
--------------------------------

``RETURN_VALUE`` 做的事情比看起来多得多：

.. code-block:: c

    TARGET(RETURN_VALUE) {
        next_instr += 1;

        // 1. 从栈顶取出返回值
        retval = stack_pointer[-1];
        stack_pointer += -1;

        // 2. 确保返回值跨帧安全
        _PyStackRef temp = PyStackRef_MakeHeapSafe(retval);

        // 3. 弹出当前帧，恢复调用者的帧
        _PyInterpreterFrame *dying = frame;
        frame = tstate->current_frame = dying->previous;
        _PyEval_FrameClearAndPop(tstate, dying);

        // 4. 恢复调用者的指令指针
        stack_pointer = _PyFrame_GetStackPointer(frame);
        LOAD_IP(frame->return_offset);

        // 5. 将返回值压入调用者的栈
        stack_pointer[0] = res;
        stack_pointer += 1;

        DISPATCH();
    }

整个操作中，第 3 步是最关键的——帧的切换发生在函数调用的**每次返回**中。

通过示例脚本验证
----------------

运行 :file:`examples/bytecodes_demo.py`：

.. code-block:: text

    --- 指令频次统计 ---
    add(1, 2) 的指令分布：
    RESUME:          1
    LOAD_FAST:       2  (已被超指令合并)
    LOAD_CONST:      1
    BINARY_OP:       1
    RETURN_VALUE:    1

    --- 比较操作符的分发 ---
    1 < 2:   COMPARE_OP (LT)
    1 == 2:  COMPARE_OP (EQ)
    'a' in 'abc':  CONTAINS_OP

    --- 函数调用链的指令追踪 ---
    CALL 指令的参数解析：
    f(1, 2, 3):  oparg = 3

    --- 跳转指令 ---
    循环的 JUMP_BACKWARD

小结
----

.. list-table::
   :header-rows: 1

   * - 指令组
     - 代表性指令
     - C 层核心操作
   * - 局部变量加载/存储
     - ``LOAD_FAST`` 、``STORE_FAST``
     - ``GETLOCAL(oparg)`` / 直接数组索引
   * - 常量加载
     - ``LOAD_CONST``
     - ``co_consts[oparg]``
   * - 二元运算
     - ``BINARY_OP``
     - ``Py_BinaryOp(lhs, rhs, oparg)``
   * - 函数调用
     - ``CALL``
     - ``PyObject_Vectorcall(...)``
   * - 流程控制
     - ``JUMP_*`` 、``POP_JUMP_IF_*``
     - ``next_instr += offset``
   * - 超指令 (3.14)
     - ``LOAD_FAST_LOAD_FAST`` 等
     - 一次加载两个局部变量

参考资料
--------

- :ref:`ceval-loop` — 解释循环如何分发这些指令
- :ref:`ceval-specialize` — 特化改写指令的机制
- :file:`Python/ceval.c` — 指令分发表
- :file:`Include/internal/pycore_opcode.h` — 操作码定义
