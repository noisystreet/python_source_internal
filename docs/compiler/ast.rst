抽象语法树 (AST) — 语法结构的中间表示
=============================================

AST（Abstract Syntax Tree）是 Parser 的输出、Compiler 的输入——它是
源代码语法结构的树状表示，不包含具体语法细节（如括号、分号）。

从一道题开始
------------

.. code-block:: python

    >>> import ast
    >>> ast.dump(ast.parse("x + 42"))
    "Module(body=[Expr(value=BinOp(left=Name(id='x'), op=Add(), right=Constant(42)))])"

AST 去掉了括号、缩进、分号等语法糖，保留了代码的逻辑结构。

.. mermaid::

    flowchart LR
        parser["Parser (PEG)"] --> ast["AST (mod_ty / expr_ty / stmt_ty)"]
        ast --> compiler["Compiler → 字节码"]

第一问：AST 节点类型
-------------------

AST 节点定义在 :file:`Python/Python-ast.c` 中，由 :file:`Parser/Python.asdl`
自动生成。所有节点分为三类：

.. code-block:: text

    mod_ty:   Module | Interactive | Expression  (模块级)
    stmt_ty:  If | For | While | Assign | Pass | Return ... (语句)
    expr_ty:  BinOp | Name | Constant | Call | ... (表达式)

每个节点是一个 C 结构体，通过 ``kind`` 字段区分具体类型：

.. code-block:: c

    typedef struct _stmt *stmt_ty;
    struct _stmt {
        enum _stmt_kind kind;  // If_kind, For_kind, ...
        union {
            struct { expr_ty test; asdl_stmt_seq *body; ... } If;
            struct { expr_ty target; expr_ty value; ... } Assign;
            // ...
        } v;
        int lineno;
        int col_offset;
        int end_lineno;
        int end_col_offset;
    };

关键设计：

- ``kind`` 字段指示是哪种语句/表达式
- ``v`` 联合体根据 ``kind`` 存储不同的子节点
- 位置信息（行号/列号）记录在每个节点中

第二问：ASDL 定义
----------------

AST 的结构由 :file:`Parser/Python.asdl` 描述：

.. code-block:: text

    -- 一个简化的 ASDL 定义片段
    module Python {
        stmt = If(expr test, stmt* body, stmt* orelse)
              | For(expr target, expr iter, stmt* body, stmt* orelse)
              | ...

        expr = BinOp(expr left, operator op, expr right)
              | Name(identifier id, expr_context ctx)
              | Constant(constant value)
              | ...
    }

:file:`Python-ast.c` 和 :file:`Python-ast.h` 由工具从 ASDL 文件自动生成。

通过示例脚本验证
---------------

运行 :file:`examples/ast_demo.py`：

.. code-block:: text

    --- AST 遍历 ---
    Fibonacci 函数的 AST 节点总数: 45
    节点类型数: 15

    --- AST 节点位置信息 ---
    每个节点都记录了源码中的行号和列号

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - AST 是什么？
     - 源码的树状结构表示，不包含语法细节
   * - 节点分几类？
     - mod_ty / stmt_ty / expr_ty
   * - 节点定义在哪？
     - Python.asdl → Python-ast.c（自动生成）
   * - AST 去哪？
     - 作为 Compiler 的输入，生成字节码
