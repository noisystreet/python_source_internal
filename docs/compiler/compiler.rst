.. _compiler-compiler:

字节码生成 (Compiler) — 从 AST 到字节码
================================================

.. epigraph::

   "All language designers are dissatisfied with their own creations."

   -- Paul Graham


Compiler 是整个编译流程的最后一步——它将 AST 转换为 CPython 字节码
（``PyCodeObject`` ），然后交由 ceval 解释器执行。

从一道题开始
------------

.. code-block:: text

    AST: BinOp(left=Name('x'), op=Add(), right=Constant(42))

    ↓ Compiler (Python/compile.c)

    Bytecode:
    0 LOAD_NAME     x
    2 LOAD_CONST    42
    4 BINARY_OP     +
    8 RETURN_VALUE

第一问：Compiler 的结构
-----------------------

Compiler 的核心是 ``compiler`` 结构体：

.. code-block:: c

    struct compiler {
        PyObject *c_filename;       // 文件名
        struct compiler_unit *u;    // 当前编译单元
        PyObject *c_stack;          // 编译单元栈
        PyFutureFeatures *c_future; // future 特性
    };

每个编译单元（``compiler_unit`` ）对应一个作用域——模块、函数、类：

.. code-block:: c

    struct compiler_unit {
        PySTEntryObject *u_ste;    // 符号表条目
        PyObject *u_name;          // 名称
        basicblock *u_blocks;      // 所有基本块
        basicblock *u_curblock;    // 当前基本块
        int u_nextblock;           // 下一个基本块编号
        struct instr *u_instr;     // 指令列表
        int u_ninstrs;             // 指令数
        int u_firstlineno;         // 第一行行号
    };

第二问：基本块和指令
--------------------

Compiler 将代码划分为**基本块 (basic block)**——每个块是一系列顺序执行的指令，
入口唯一、出口唯一（跳转到另一块）。

.. code-block:: c

    typedef struct basicblock {
        struct instr *b_instr;     // 指令数组
        int b_iused;               // 已用指令数
        int b_iallocated;          // 已分配容量
        struct basicblock *b_next; // 链表
    } basicblock;

    typedef struct instr {
        int i_opcode;       // 操作码
        int i_oparg;        // 操作参数
    } instr;

Compiler 的核心函数是 ``compiler_visit_stmt`` 和 ``compiler_visit_expr``——
它们根据 AST 节点类型分发到对应的代码生成函数。

.. mermaid::

    flowchart TD
        ast["AST 节点"] --> dispatch{"节点类型?"}
        dispatch -->|"If"| compiler_if["compiler_if<br/>生成 JUMP_IF 指令"]
        dispatch -->|"BinOp"| compiler_binop["compiler_binop<br/>生成 BINARY_OP"]
        dispatch -->|"Call"| compiler_call["compiler_call<br/>生成 CALL"]

第三问：栈深度计算
------------------

Compiler 在生成代码后计算**评估栈的最大深度** ：

.. code-block:: c

    static int compute_stack_depth(PyCodeObject *co) {
        // 遍历所有指令，模拟栈深度变化
        int depth = 0, max_depth = 0;
        for (each instruction) {
            depth += stack_effect(opcode, oparg);
            max_depth = max(max_depth, depth);
        }
        return max_depth;
    }

这个值被存储在 ``PyCodeObject.co_stacksize`` 中，解释器用它预分配栈空间。

通过示例脚本验证
----------------

运行 :file:`examples/compiler_demo.py`：

.. code-block:: text

    --- 代码对象的创建 ---
    compile('x = 42', '', 'exec')
    → <code object <module> ...>

    --- 代码对象属性 ---
    co_argcount: 0
    co_nlocals: 1
    co_stacksize: 1
    co_flags: 19
    co_consts: (42, None)
    co_varnames: ('x',)
    co_names: ()
    co_filename: ...

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - Compiler 输入/输出？
     - 输入 AST，输出 PyCodeObject
   * - 基本块是什么？
     - 顺序执行的指令序列
   * - 栈深度怎么算？
     - 模拟指令对栈的影响
   * - 编译单元是什么？
     - 每个作用域对应一个 compiler_unit

参考资料
--------

- :ref:`ceval-loop` — 解释循环如何执行生成的字节码
- :ref:`ceval-bytecodes` — 字节码指令集详解
- :file:`Python/compile.c` — 字节码生成
