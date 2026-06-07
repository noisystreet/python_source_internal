解释循环主流程 — 字节码引擎的心脏
========================================

CPython 的核心是一个**栈式字节码解释器**。它读取编译生成的字节码指令，一条一条地执行。

从一道题开始
------------

.. code-block:: python

    def add(a, b):
        c = a + b
        return c

    import dis
    dis.dis(add)

输出：

.. code-block:: text

    0 RESUME              0
    2 LOAD_FAST_LOAD_FAST 1 (a, b)  # 同时把 a 和 b 压入栈
    4 BINARY_OP            0 (+)    # 弹出栈顶两个，相加，结果压入栈
    6 STORE_FAST           2 (c)    # 弹出栈顶，存入局部变量 c
    8 LOAD_FAST            2 (c)    # 把 c 压入栈
    10 RETURN_VALUE                  # 返回栈顶值

关键问题是：**这些指令在 C 层是怎么被执行的？**

答案就在 ``_PyEval_EvalFrameDefault`` 函数中——CPython 的解释循环。

第一问：谁驱动了解释循环？
--------------------------

解释循环的入口是 ``_PyEval_EvalFrameDefault``：

.. code-block:: c

    // Python/ceval.c
    PyObject *
    _PyEval_EvalFrameDefault(PyThreadState *tstate,
                              _PyInterpreterFrame *frame,
                              int throwflag)
    {
        // 1. 初始化局部变量（next_instr, stack_pointer 等）
        // 2. 进入指令分发循环
        // 3. 对每条指令执行对应的 C 代码
        // 4. 函数返回时清理帧
    }

调用链如下：

.. mermaid::

    flowchart TD
        python["Python: add(3, 5)"] --> ceval["PyObject_Call → _PyEval_EvalFrame"]
        ceval --> loop["_PyEval_EvalFrameDefault(tstate, frame)"]
        loop --> dispatch["读取 instr_ptr 处的指令"]
        dispatch --> execute["执行指令对应的 C 代码"]
        execute --> next_dispatch["instr_ptr += 指令长度<br/>继续下一条"]
        next_dispatch --> dispatch
        execute --> return_result["遇到 RETURN_VALUE → 返回结果"]

第二问：帧 (_PyInterpreterFrame) 是什么？
-----------------------------------------

每次函数调用都会创建一个帧。帧是解释器执行代码的上下文：

.. code-block:: c

    struct _PyInterpreterFrame {
        _PyStackRef f_executable;   // 代码对象引用
        struct _PyInterpreterFrame *previous;  // 上一个帧（调用者）
        _PyStackRef f_funcobj;      // 函数对象
        PyObject *f_globals;        // 全局命名空间
        PyObject *f_builtins;       // 内置命名空间
        PyObject *f_locals;         // 局部命名空间
        PyFrameObject *frame_obj;   // Python 层可见的帧对象
        _Py_CODEUNIT *instr_ptr;    // ★ 当前执行到哪条指令
        _PyStackRef *stackpointer;  // ★ 栈顶指针
        uint16_t return_offset;     // 返回地址偏移
        char owner;                 // 帧所有者（C 栈/生成器/解释器）
        _PyStackRef localsplus[1];  // 局部变量 + 评估栈
    };

关键字段：

- ``instr_ptr``：指向当前正在执行的字节码指令。每执行完一条指令就前移
- ``stackpointer``：指向当前评估栈的栈顶
- ``previous``：指向调用者的帧——函数返回时恢复
- ``localsplus``：既是局部变量存储区，也是评估栈的空间

.. mermaid::

    flowchart LR
        subgraph Frame["_PyInterpreterFrame"]
            ip["instr_ptr → LOAD_FAST"]
            sp["stackpointer → 栈顶"]
            locals["localsplus<br/>[a, b, c, 栈空间...]"]
        end
        subgraph Code["代码对象"]
            bc["字节码: [RESUME, LOAD_FAST, LOAD_FAST, BINARY_OP, ...]"]
        end
        ip --> bc

第三问：指令是如何分发的？
--------------------------

CPython 3.14 使用**尾调用解释器 (Tail-Call Interpreter)** 模型。
每执行完一条指令，就通过函数调用跳到下一条指令的入口。所有指令的实现都在
:file:`generated_cases.c.h` 中：

.. code-block:: c

    // generated_cases.c.h (由 Tools/cases_generator 自动生成)
    TARGET(BINARY_OP) {
        // 1. 读操作数和操作码
        rhs = stack_pointer[-1];
        lhs = stack_pointer[-2];
        // 2. 执行运算
        res = _Py_BinaryOp(lhs_o, rhs_o, oparg);
        // 3. 写回结果
        stack_pointer[-2] = res;
        stack_pointer--;
        // 4. 派发下一条指令
        DISPATCH();
    }

每个 ``TARGET(op)`` 宏展开为一个函数（尾调用模式）或 ``case`` 标签（switch 模式）。

指令的通用结构：

#. 从栈上弹出操作数
#. 执行操作
#. 将结果压回栈
#. 更新 ``instr_ptr``（前移）
#. 调用 ``DISPATCH`` 跳转到下一条指令

第四问：评估栈如何工作？
------------------------

CPython 是**栈式虚拟机**，大多数指令都是：

- **压栈**（LOAD_*）: 将某个值放到栈顶 ``stack_pointer++``
- **弹栈**（STORE_*）: 从栈顶取值 ``stack_pointer--``
- **运算**（BINARY_*）: 弹出操作数，运算，压入结果

.. code-block:: text

    执行 add(3, 5) 时的栈状态变化：

    LOAD_FAST    a          →  [3]
    LOAD_FAST    b          →  [3, 5]
    BINARY_OP    +          →  [8]
    STORE_FAST   c          →  []
    LOAD_FAST    c          →  [8]
    RETURN_VALUE            →  返回 8

评估栈和局部变量共享同一个 ``localsplus[]`` 数组。前 ``co_nlocals``
个位置是局部变量，后面的位置是评估栈的空间。

.. mermaid::

    flowchart LR
        subgraph localsplus["localsplus[]"]
            section1["局部变量区 (a, b, c)"]
            section2["评估栈区"]
        end
        sp["stackpointer"] --> section2

第五问：RESUME 和异常处理
--------------------------

``RESUME`` 是每条代码对象的**第一条指令**。它负责：

- 检查是否需要处理挂起的生成器（``yield`` 恢复）
- 检查异步生成器钩子
- 触发监控事件（PEP 669）

当指令执行中出现异常时（例如 ``ZeroDivisionError``），

#. 指令返回 NULL
#. 解释循环跳转到 ``error`` 标签
#. 在 ``localsplus`` 中查找异常处理入口（``co_exceptiontable``）
#. 如果找到 ``try`` 块，跳转到对应的 ``SETUP_FINALLY`` / ``PUSH_EXC_INFO`` 位置
#. 如果没找到，沿着 ``frame->previous`` 链向上层帧传播

.. mermaid::

    flowchart TD
        exec["执行指令"] --> success{"返回 NULL?"}
        success -->|"否, 正常"| dispatch["DISPATCH 下一条"]
        success -->|"是, 异常"| error["goto error 标签"]
        error --> handler{"有 except 处理器?"}
        handler -->|"有"| setup["跳到 except 块"]
        handler -->|"无"| unwind["展开帧栈, 向上传播"]
        unwind --> parent["调用者的帧"]

第六问：尾调用解释器的优势
--------------------------

CPython 3.14 的尾调用解释器相对于传统 ``switch`` 解释器的优势：

- **分支预测更好**：每个指令实现是独立的函数，CPU 分支预测器不会因为 ``switch`` 的
  巨大跳转表而混乱
- **编译器可以内联**：每条指令的 C 代码可以独立优化
- **代码生成自动化**：``generated_cases.c.h`` 由 :file:`Tools/cases_generator`
  从 :file:`Python/bytecodes.c` 自动生成，减少人为错误
- **易于添加新指令**：只需在 ``bytecodes.c`` 中添加定义，重新生成即可

通过示例脚本验证
----------------

运行 :file:`examples/ceval_loop_demo.py`：

.. code-block:: text

    --- 字节码反汇编 ---
    add(3, 5) 的字节码：
    0 RESUME
    2 LOAD_FAST    a
    4 LOAD_FAST    b
    6 BINARY_OP    +
    10 STORE_FAST   c
    12 LOAD_FAST    c
    14 RETURN_VALUE

    --- 帧模拟 ---
    LOAD_FAST  a → 栈: [3]
    LOAD_FAST  b → 栈: [3, 5]
    BINARY_OP  + → 栈: [8]      # 3 + 5 = 8
    STORE_FAST c → 栈: []
    LOAD_FAST  c → 栈: [8]
    RETURN_VALUE → 返回: 8

    --- 函数调用链 ---
    outer() → inner() → inner() 返回 → outer() 返回

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 解释循环入口
     - ``_PyEval_EvalFrameDefault``
   * - 帧是什么？
     - ``_PyInterpreterFrame``，存着指令指针、栈指针、局部变量
   * - 指令如何分发？
     - 尾调用解释器：每条指令是一个函数，用 DISPATCH 跳转
   * - 评估栈怎么用？
     - 和局部变量共享 localsplus[]，LOAD 压栈，STORE 弹栈
   * - 异常怎么传播？
     - 沿帧链向上，查找 co_exceptiontable 中的处理入口
   * - 尾调用模式优势
     - 更好的分支预测、独立优化、自动生成

参考资料
--------

- :pep:`659` — 自适应解释器（特化与内联缓存）
- :file:`Python/ceval.c` — Tier 1 主循环
- :file:`Python/ceval_macros.h` — ``DISPATCH`` / ``GOTO_*`` 宏
- `CPython 3.14 ceval 设计文档 <https://docs.python.org/3.14/howto/ceval.html>`__

