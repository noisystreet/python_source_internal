符号表 (Symtable) — 作用域与名字绑定
============================================

.. epigraph::

   "What's in a name? That which we call a rose by any other name would smell as sweet."

   -- William Shakespeare, Romeo and Juliet (on scope and names)


符号表是编译过程中的一个关键阶段——在 AST 生成后、字节码生成前，
它分析每个名字（变量、函数、类）在哪个作用域定义、在哪引用。

从一道题开始
------------

.. code-block:: python

    x = 10          # 模块作用域：全局变量
    def f():
        y = 20      # 函数作用域：局部变量
        global x    # 声明 x 是全局的
        print(y)    # 引用 y

符号表需要回答：``x`` 是全局还是局部？``y`` 是函数作用域还是模块作用域？
闭包中哪些变量需要从外部捕获？

第一问：符号表的结构
--------------------

``struct symtable`` 是整个符号表，``PySTEntryObject`` 是每个作用域的条目：

.. code-block:: c

    struct symtable {
        struct _symtable_entry *st_cur;  // 当前作用域
        struct _symtable_entry *st_top;  // 模块作用域
        PyObject *st_blocks;             // AST 地址 → 条目映射
        PyObject *st_stack;              // 作用域栈
    };

    typedef struct _symtable_entry {
        PyObject *ste_symbols;    // dict: 名字 → 标志位
        PyObject *ste_varnames;   // list: 函数参数名
        PyObject *ste_children;   // list: 子作用域
        _Py_block_ty ste_type;    // 作用域类型
        int ste_nested;           // 是否嵌套
        unsigned ste_generator : 1;   // 是否是生成器
        unsigned ste_coroutine : 1;   // 是否是协程
        // ...
    } PySTEntryObject;

``ste_symbols`` 记录每个名字的标志：

.. code-block:: c

    #define DEF_GLOBAL   1    // global 声明
    #define DEF_LOCAL    2    // 本地赋值
    #define DEF_PARAM    4    // 函数参数
    #define DEF_NONLOCAL 8    // nonlocal 声明
    #define USE          16   // 名字使用

第二问：作用域类型
------------------

.. code-block:: c

    typedef enum _block_type {
        FunctionBlock,      // 函数作用域
        ClassBlock,         // 类作用域
        ModuleBlock,        // 模块作用域
        AnnotationBlock,    // 注解作用域
        TypeAliasBlock,     // 类型别名 (PEP 695)
        TypeParametersBlock,// 类型参数
        TypeVariableBlock,  // 类型变量
    } _Py_block_ty;

第三问：名字的作用域判定
------------------------

``_PyST_GetScope`` 返回名字的作用域：

.. code-block:: c

    #define LOCAL             1   // 局部变量
    #define GLOBAL_EXPLICIT   2   // 显式 global
    #define GLOBAL_IMPLICIT   3   // 隐式全局
    #define FREE              4   // 自由变量（需闭包捕获）
    #define CELL              5   // 单元变量（被嵌套函数引用）

通过示例脚本验证
----------------

运行 :file:`examples/symtable_demo.py`：

.. code-block:: text

    --- 模块作用域 ---
    'x': 全局

    --- 函数作用域 ---
    'y': 局部
    'x': 全局 (global 声明)

    --- 闭包 ---
    inner 捕获 outer 的 'x':
    'x' 是 CELL (在 outer 中)
    'x' 是 FREE (在 inner 中)

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 符号表做什么？
     - 分析名字的作用域和绑定关系
   * - 作用域分几种？
     - Module / Function / Class / Annotation / TypeAlias 等
   * - 名字有哪几种作用域？
     - LOCAL / GLOBAL / FREE / CELL
   * - 闭包怎么实现的？
     - FREE 变量从外层作用域捕获，CELL 变量被内层引用

参考资料
--------

- :file:`Python/symtable.c` — 符号表实现
