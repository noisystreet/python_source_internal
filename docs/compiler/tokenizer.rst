Tokenizer — 词法分析器
=============================

编译系统的第一站是将源代码文本转换为**词法单元（token）流**。CPython 3.14 使用
一个手写的词法分析器（tokenizer），将它从传统的 `Parser/tokenizer/` 移到了
`Parser/lexer/`，并完全重写以更好地支持 f-string 嵌套。

从一道题开始
------------

.. code-block:: python

    x = 42 + (y - 1)  # source text

    # 经过 tokenizer 后：
    NAME 'x'
    OP   '='
    NUMBER '42'
    OP   '+'
    OP   '('
    NAME 'y'
    OP   '-'
    NUMBER '1'
    OP   ')'
    NEWLINE
    ENDMARKER

Tokenizer 的工作就是将源代码流切分为这样一个一个的 token。

.. mermaid::

    flowchart LR
        src["source.py<br/>x = 42 + y"] --> tokenizer["Tokenizer<br/>(Parser/lexer/)"]
        tokenizer --> tokens["Token 流<br/>NAME → OP → NUMBER → OP → NAME"]
        tokens --> parser["Parser<br/>(PEG 语法分析)"]

第一问：Tokenizer 的状态结构
----------------------------

Tokenizer 的核心是 ``struct tok_state``，它保存了词法分析的所有状态：

.. code-block:: c

    struct tok_state {
        // 输入缓冲区：buf <= cur <= inp <= end
        char *buf;          // 输入缓冲区起始
        char *cur;          // 当前读取位置
        char *inp;          // 缓冲区中有效数据末尾
        const char *end;    // 缓冲区末尾
        const char *start;  // 当前 token 起始

        int done;           // 状态：E_OK / E_EOF / 错误码
        int lineno;         // 当前行号
        int col_offset;     // 当前列偏移

        // 缩进栈
        int indent;
        int indstack[MAXINDENT]; // 缩进层级栈
        int pendin;             // 待处理的缩进/反缩进

        // 括号嵌套栈
        int level;
        char parenstack[MAXLEVEL];

        // f-string 模式栈（支持嵌套）
        tokenizer_mode tok_mode_stack[MAXFSTRINGLEVEL];
        int tok_mode_stack_index;

        // ...
    };

关键字段：

- ``cur`` / ``inp`` / ``end``：三点指针，用于管理输入缓冲区
- ``start`` / ``end``：标记当前 token 的起止位置
- ``indent`` / ``indstack``：用于处理 Python 的缩进
- ``tok_mode_stack``：f-string 模式栈，用于处理 f-string 的嵌套

第二问：词法分析的流程
-----------------------

每次调用 ``_PyTokenizer_Get`` 读取下一个 token：

.. mermaid::

    flowchart TD
        get["_PyTokenizer_Get(tok, token)"] --> skip["跳过空白和注释"]
        skip --> eol{"行尾?"}
        eol -->|"是"| indent["计算缩进<br/>产生 INDENT/DEDENT/NEWLINE"]
        indent --> next
        eol -->|"否"| char{"当前字符?"}
        char -->|"字母或 _"| name["读标识符/关键字<br/>→ NAME"]
        char -->|"数字"| number["读数字<br/>→ NUMBER"]
        char -->|"引号"| string["读字符串/f-string<br/>→ STRING"]
        char -->|"运算符"| op["匹配运算符<br/>→ OP"]
        char -->|"#"| comment["跳过注释"]
        char -->|"EOF"| end["→ ENDMARKER"]

每个字符的判断都是通过 ``tok->cur`` 处的字符值进行 switch 分发。

第三问：缩进处理
----------------

Python 使用缩进表示代码块。Tokenizer 维护一个**缩进栈**：

.. code-block:: c

    // 遇到行尾时处理缩进
    if (tok->atbol) {
        // 计算行的缩进级别
        int col = 0;
        while (*tok->cur == ' ' || *tok->cur == '\t') {
            if (*tok->cur == '\t')
                col = (col / tok->tabsize + 1) * tok->tabsize;
            else
                col++;
            tok->cur++;
        }

        if (col > tok->indstack[tok->indent]) {
            // 缩进增加 → 产生 INDENT token
            tok->indent++;
            tok->pendin++;
        }
        else if (col < tok->indstack[tok->indent]) {
            // 缩进减少 → 产生 DEDENT token(s)
            while (col < tok->indstack[tok->indent]) {
                tok->indent--;
                tok->pendin--;
            }
        }
    }

INDENT 和 DEDENT token 在解析阶段被映射为代码块的开始和结束。

第四问：f-string 的嵌套支持
---------------------------

CPython 3.14 重写了 tokenizer，以正确支持 f-string 的嵌套：

.. code-block:: python

    f"hello {name.upper()!r} world {a + b}"

Tokenizer 在遇到 ``f"`` 时推入 ``TOK_FSTRING_MODE``：

.. code-block:: c

    // tok_mode_stack 用于追踪 f-string 的嵌套
    struct _tokenizer_mode {
        enum tokenizer_mode_kind_t kind;  // TOK_REGULAR_MODE 或 TOK_FSTRING_MODE
        int curly_bracket_depth;          // 当前 f-string 花括号深度
        int curly_bracket_expr_start_depth; // 表达式开始深度
        char quote;                       // 引号字符
        int quote_size;                   // 引号个数 (1 或 3)
        // ...
    };

每个嵌套的 f-string 都会在栈上推入一个新的模式上下文。

第五问：Token 的表示
---------------------

每个 token 使用 ``struct token`` 表示：

.. code-block:: c

    struct token {
        int level;             // 括号嵌套层级
        int lineno;            // 行号
        int col_offset;        // 列偏移
        int end_lineno;        // 结束行号
        int end_col_offset;    // 结束列偏移
        const char *start;     // 指向源代码中的起始位置
        const char *end;       // 指向源代码中的结束位置
        PyObject *metadata;    // 额外元数据（字符串值等）
    };

注意 ``start`` 和 ``end`` 指向的是**原始源代码缓冲区**中的位置，
而不是拷贝出来的字符串。这避免了不必要的内存分配。

通过示例脚本验证
----------------

运行 :file:`examples/tokenizer_demo.py`：

.. code-block:: text

    --- 从源码到 token ---
    'x = 42 + (y - 1)'
    行 1: NAME     'x'     (1,0)-(1,1)
    行 1: OP       '='     (1,2)-(1,3)
    行 1: NUMBER   '42'    (1,4)-(1,6)
    行 1: OP       '+'     (1,7)-(1,8)
    行 1: OP       '('     (1,9)-(1,10)
    行 1: NAME     'y'     (1,10)-(1,11)
    行 1: OP       '-'     (1,12)-(1,13)
    行 1: NUMBER   '1'     (1,14)-(1,15)
    行 1: OP       ')'     (1,16)-(1,17)
    行 1: NEWLINE
    行 2: ENDMARKER

    --- 关键字识别 ---
    'if'  → NAME (keyword)
    'for' → NAME (keyword)
    'xyz' → NAME (identifier)

    --- 缩进处理 ---
    def f():
        if x:
            pass

    行 1: NAME 'def' ...
    行 1: NAME 'f' ...
    行 1: OP '(' ')'
    行 1: OP ':'
    行 1: NEWLINE INDENT
    行 2: NAME 'if' ... INDENT
    行 3: NAME 'pass' ...
    行 3: NEWLINE DEDENT DEDENT

    --- 字符串解析 ---
    '"hello"'         → STRING
    'b"bytes"'        → STRING
    'f"hello {name}"' → STRING (f-string)

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - Tokenizer 做什么？
     - 把源码切分为 token 流
   * - 核心数据结构？
     - ``struct tok_state`` 保存所有状态
   * - 缩进怎么处理？
     - 缩进栈 ``indstack[]`` 产生 INDENT/DEDENT
   * - f-string 嵌套怎么支持？
     - ``tok_mode_stack`` 模式栈
   * - Token 怎么存储？
     - ``struct token``，start/end 指向原始缓冲区
   * - Tokenizer 和 Parser 谁先执行？
     - Tokenizer 先，Parser 后
