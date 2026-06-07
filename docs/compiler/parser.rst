语法分析器 (Parser) — PEG 语法分析
============================================

CPython 3.9+ 使用 **PEG (Parsing Expression Grammar)** 解析器替代了
原来的 LL(1) 解析器。PEG 解析器更强大、更易于维护，支持直接表达
Python 语法的复杂性。

从一道题开始
------------

.. code-block:: text

    Token 流:
    NAME 'if' → NAME 'x' → OP ':' → NEWLINE → INDENT → NAME 'pass'

    # 经过 Parser 后：
    If(
        test=Name('x'),
        body=[Pass()],
        orelse=[]
    )

Parser 的工作就是将扁平的 token 流转换成**抽象语法树 (AST)**。

.. mermaid::

    flowchart LR
        tokens["Token 流<br/>NAME → OP → NAME → ..."] --> parser["PEG Parser<br/>(Parser/pegen.c)"]
        parser --> ast["抽象语法树<br/>mod_ty (AST 节点)"]
        parser --> grammar["语法规则<br/>python.gram → parse.c"]

第一问：PEG 解析器结构
-----------------------

``Parser`` 结构体是解析器的核心：

.. code-block:: c

    typedef struct {
        struct tok_state *tok;    // tokenizer 状态
        Token **tokens;           // token 缓存
        int mark;                 // 当前解析位置（token 索引）
        int fill, size;           // token 缓存填充数和大小
        PyArena *arena;           // AST 节点内存分配器
        int start_rule;           // 起始语法规则
        int *errcode;             // 错误码
        int flags;                // 解析标志
        int feature_version;      // Python 特性版本
        // ...
    } Parser;

关键字段：

- ``tok``：指向 tokenizer 状态（负责从源码获取 token）
- ``tokens``：token 缓存数组（避免重复词法分析）
- ``mark``：当前解析位置（类似"文件指针"）
- ``arena``：AST 节点的内存分配器——所有 AST 节点从这里分配

第二问：PEG 语法规则
--------------------

PEG 语法定义在 :file:`python.gram` 中。它被工具 :file:`Tools/peg_generator`
编译成 :file:`Parser/parse.c`。

一个典型的语法规则：

.. code-block:: text

    # python.gram 中的 if 语句规则
    if_stmt[stmt_ty]:
        | 'if' named_expression ':' block elif_stmt else_stmt {
            _PyAST_If(p, named_expression, block, elif_stmt_else, ...) }
        | 'if' named_expression ':' block  { _PyAST_If(p, ...) }

每条规则包含：

- **规则名**：``if_stmt``
- **返回类型**：``stmt_ty``（AST 节点类型）
- **备选项**：用 ``|`` 分隔，每个备选项是一系列符号（token 或子规则）
- **动作**：``{ ... }`` 中的 C 代码，构造 AST 节点

PEG 的**有序选择**语义：尝试第一个备选项，如果失败则回退并尝试下一个。

.. mermaid::

    flowchart TD
        if_stmt["if_stmt"] --> alt1["备选 1: 'if' expr ':' block 'elif' ..."]
        if_stmt --> alt2["备选 2: 'if' expr ':' block"]
        alt1 --> try1["尝试匹配"]
        try1 -->|"成功"| result1["构造 if-elif-else AST"]
        try1 -->|"失败"| alt2
        alt2 --> try2["尝试匹配"]
        try2 -->|"成功"| result2["构造 if AST"]
        try2 -->|"失败"| fail["返回 NULL"]

第三问：解析流程
---------------

``_PyPegen_run_parser`` 是解析器的入口：

.. code-block:: c

    void *_PyPegen_run_parser(Parser *p)
    {
        // 调用起始规则的解析函数
        return _PyPegen_parse(p);
    }

``_PyPegen_parse`` 是 :file:`parse.c` 中自动生成的函数。它从起始规则
（通常是 ``file``）开始递归下降解析。

每个解析步骤的核心模式：

.. code-block:: c

    // 手动实现的 PEG 解析器模式
    static void *parse_if_stmt(Parser *p)
    {
        int mark = p->mark;  // 保存当前位置

        // 尝试第一个备选项
        if (_PyPegen_expect_token(p, IF_KEYWORD)
            && (test = parse_named_expression(p))
            && _PyPegen_expect_token(p, COLON)
            && (body = parse_block(p))
            && (elif = parse_elif_stmt(p))
            && (else_ = parse_else_stmt(p))) {
            // 成功：构造 AST 节点
            return _PyAST_If(p, test, body, elif_else, ...);
        }

        // 失败：恢复位置并尝试下一个
        p->mark = mark;
        // ... 尝试第二个备选项 ...

        return NULL;  // 所有备选项都失败
    }

关键字：

- **回溯 (Backtracking)**：失败时恢复 ``p->mark`` 回到尝试前的位置
- **备忘录 (Memoization)**：``Memo`` 结构缓存已解析的结果，避免重复解析
- **向前看 (Lookahead)**：``_PyPegen_lookahead`` 用于不消耗 token 的检查

第四问：AST 节点的创建
-----------------------

所有 AST 节点通过 ``PyArena`` 分配：

.. code-block:: c

    // _PyAST_If 在 Python/Python-ast.c 中
    stmt_ty _PyAST_If(expr_ty test, asdl_stmt_seq *body,
                      asdl_stmt_seq *orelse, int lineno, int col_offset,
                      int end_lineno, int end_col_offset, PyArena *arena)
    {
        stmt_ty p = (stmt_ty)PyArena_Malloc(arena, sizeof(stmt_ty));
        p->kind = If_kind;
        p->v.If.test = test;
        p->v.If.body = body;
        p->v.If.orelse = orelse;
        p->lineno = lineno;
        p->col_offset = col_offset;
        // ...
        return p;
    }

``PyArena`` 是一个简单的 bump allocator——分配时从不释放，整个解析结束后一次性释放。
这简化了 AST 节点的内存管理。

第五问：错误恢复
---------------

PEG 解析器的一个弱点是**错误报告**——传统 ``if-else`` 模式的回溯可能导致
错误位置不准。CPython 的解析器通过以下方式改进：

.. code-block:: c

    // 记录最远的错误位置
    #define RAISE_SYNTAX_ERROR(msg, ...) \
        _PyPegen_raise_error(p, PyExc_SyntaxError, 0, msg, ##__VA_ARGS__)

    // 使用 known_err_token 跟踪
    if (p->known_err_token == NULL
        || p->known_err_token->lineno < last_token->lineno
        || (p->known_err_token->lineno == last_token->lineno
            && p->known_err_token->col_offset < last_token->col_offset)) {
        p->known_err_token = last_token;
    }

解析器会追踪到达的最远位置（"known error token"），在最终报告错误时，
使用这个 token 的位置，使得错误信息更准确。

通过示例脚本验证
---------------

运行 :file:`examples/parser_demo.py`：

.. code-block:: text

    --- 表达式解析 ---
    ast.dump(compile('x + 42', '', 'eval'))
    → Expression(body=BinOp(left=Name('x'), op=Add(), right=Constant(42)))

    --- if 语句解析 ---
    ast.dump(compile('if x: pass', '', 'exec'))
    → Module(body=[If(test=Name('x'), body=[Pass()], orelse=[])])

    --- 函数定义解析 ---
    ast.dump(compile('def f(x): return x', '', 'exec'))
    → ...

    --- 语法错误 ---
    错误信息: "invalid syntax" at line 1, col 5

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 用什么解析算法？
     - PEG (Parsing Expression Grammar)，递归下降 + 有序选择
   * - 语法规则在哪？
     - :file:`python.gram` → 编译为 :file:`parse.c`
   * - 怎么支持回溯？
     - 保存/恢复 ``p->mark``
   * - AST 节点怎么分配？
     - PyArena bump allocator，一次性释放
   * - 错误报告怎么改进？
     - 记录最远 token 位置 (known_err_token)
