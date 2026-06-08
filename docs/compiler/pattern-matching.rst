.. _compiler-pattern-matching:

match / case — 模式匹配的底层实现
=========================================

.. epigraph::

   "The art of being wise is the art of knowing what to overlook."

   -- William James


Python 3.10 引入的 ``match`` / ``case`` 语句（PEP 634-636）是
语言中最复杂的语法特性之一。它涉及新的 AST 节点、新的字节码指令，
以及一个用 Python 实现的模式匹配编译器。

从一道题开始
------------

.. code-block:: python

    match value:
        case 1:
            print("one")
        case str():
            print("a string")
        case _:
            print("something else")

模式匹配的编译和执行分为三个阶段：

.. mermaid::

    flowchart LR
        source["match value: ..."] --> parser["PEG 解析器<br/>MatchStmt / CaseStmt AST"]
        parser --> compiler["compile.c 编译器<br/>填充 co_exceptiontable<br/>生成 MATCH_KEYS / MATCH_CLASS 等指令"]
        compiler --> ceval["ceval.c 执行<br/>模式匹配字节码"]

第一问：AST 节点
----------------

模式匹配在 AST 层面引入了几个新节点：

.. code-block:: text

    // Python-ast.h
    MatchStmt:    match 语句（包含多个 case）
    └── CaseStmt: 单个 case（pattern + guard + body）
        ├── MatchValue:   字面值匹配 (case 1)
        ├── MatchSingleton: None/True/False 匹配
        ├── MatchSequence: 序列匹配 (case [a, b, c])
        ├── MatchMapping:  字典匹配 (case {"key": v})
        ├── MatchClass:    类型匹配 (case str(), case Point(x, y))
        ├── MatchStar:     ``*args`` 在序列匹配中
        └── MatchAs:       as 绑定 (case _ as x)

PEG 解析器处理 ``match`` 的语法规则：

.. code-block:: text

    # Parser/python.gram
    match_stmt: "match" subject ':' NEWLINE INDENT case_block+ DEDENT
    case_block: "case" patterns guard? ':' block
    patterns: pattern (',' pattern)* ','?
    pattern: or_pattern | as_pattern | class_pattern | ...
    guard: "if" named_expression

第二问：字节码指令
------------------

模式匹配新增了 5 条字节码指令：

.. list-table::
   :header-rows: 1

   * - 指令
     - 作用
     - 操作数
   * - ``MATCH_KEYS``
     - 提取字典的键列表用于匹配
     - 键元组
   * - ``MATCH_CLASS``
     - 检查类型并提取属性
     - 类型 + 属性名元组
   * - ``MATCH_MAPPING``
     - 检查是否是映射类型
     - 无
   * - ``MATCH_SEQUENCE``
     - 检查是否是序列类型
     - 无
   * - ``MATCH_STAR``
     - 处理序列匹配中的 ``*args``
     - 无

第三问：模式匹配的编译策略
--------------------------

CPython 的模式匹配编译器是一个用 Python 写的**源码到字节码的翻译器**，
位于 ``Lib/_compiler/patterns.py``：

.. code-block:: python

    # Lib/_compiler/patterns.py（简化）
    def compile_pattern(pattern, state):
        if isinstance(pattern, MatchValue):
            # 字面值匹配 → 编译为比较指令
            return [
                ("LOAD_CONST", pattern.value),
                ("COMPARE_OP", "=="),
                ("JUMP_IF_NOT_MATCH", fail_label),
            ]
        elif isinstance(pattern, MatchClass):
            # 类型匹配 → 先检查类型，再提取属性
            return [
                ("MATCH_CLASS", pattern.cls, pattern.names),
                ("JUMP_IF_NOT_MATCH", fail_label),
                # 成功后，属性值已在栈上
            ]
        elif isinstance(pattern, MatchAs):
            # 绑定匹配 → 直接 STORE_FAST
            return [("STORE_FAST", pattern.name)]

失败时跳转的标签由 ``co_exceptiontable`` 中的异常处理条目管理——和 ``try/except``
的失败跳转使用相同的机制。

第四问：性能考虑
----------------

模式匹配的 C 层实现（``MATCH_CLASS``、``MATCH_KEYS`` 等）是经过性能优化的：

.. code-block:: c

    // Python/ceval.c — MATCH_CLASS 的简化实现
    case TARGET(MATCH_CLASS): {
        PyObject *subject = TOP();
        PyObject *cls = oparg;   // 目标类型
        PyObject *attrs = PEEK(2);  // 属性名元组

        // 1. 类型检查（最快路径）
        if (!PyObject_IsInstance(subject, cls)) {
            JUMP_TO_DESINATION(fail);
        }

        // 2. 提取属性值（每个属性一次 getattr）
        for (int i = 0; i < PyTuple_Size(attrs); i++) {
            PyObject *name = PyTuple_GET_ITEM(attrs, i);
            PyObject *value = PyObject_GetAttr(subject, name);
            PUSH(value);
        }

        DISPATCH();
    }

通过示例脚本验证
----------------

运行 :file:`examples/match_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - match 在 AST 层面是什么？
     - MatchStmt → CaseStmt → MatchValue / MatchClass / MatchAs 等
   * - 新增了几条字节码？
     - 5 条：MATCH_KEYS / MATCH_CLASS / MATCH_MAPPING / MATCH_SEQUENCE / MATCH_STAR
   * - 模式匹配编译器在哪？
     - Lib/_compiler/patterns.py（Python 实现）
   * - 失败时的跳转怎么实现？
     - 通过 co_exceptiontable（和 try/except 同样的机制）
   * - 字面值匹配怎么编译？
     - LOAD_CONST + COMPARE_OP + 条件跳转

参考资料
--------

- :ref:`compiler-compiler` — 模式匹配的特殊编译路径
- :ref:`compiler-symtable` — 模式匹配中的变量作用域
- :pep:`634` — 模式匹配规范
- :pep:`635` — 模式匹配动机
- :file:`Python/ceval.c` — MATCH_* 指令
