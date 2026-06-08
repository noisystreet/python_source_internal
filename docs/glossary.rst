.. _glossary:

术语表
=======

.. glossary::

   PyObject
     所有 Python 对象的 C 层基类。只包含 ``ob_refcnt`` 和 ``ob_type`` 两个字段。

   PyVarObject
     可变长对象的基类，在 ``PyObject`` 基础上增加 ``ob_size`` 字段。

   PyTypeObject
     类型对象的 C 结构体。定义了 ``tp_name``、``tp_dealloc``、``tp_call`` 等
     函数指针，是 CPython 实现"一切皆对象"和动态类型分发的核心。

   引用计数 (reference counting)
     CPython 的内存管理基础。每个对象维护 ``ob_refcnt``，当为 0 时立即回收。

   GIL (Global Interpreter Lock)
     全局解释器锁，保证同一时间只有一个线程执行 Python 字节码。

   自由线程 (Free-threading)
     3.14 中 ``--disable-gil`` 构建模式，允许多线程并行执行 Python 代码。

   BRC (Biased Reference Counting)
     平衡引用计数，自由线程构建下使用的引用计数算法。

   PyMutex
     1 字的轻量级互斥锁，用于自由线程构建中的临界区保护。

   字节码 (bytecode)
     CPython 编译器的输出，由 ``ceval.c`` 中的解释循环执行。

   Tier 2 (微码)
     自适应解释器中的第二层优化。将热点字节码翻译为更底层的微码序列。

   JIT 编译器
     将热点代码编译为机器码的技术。3.14 中使用 Copy-and-Patch 方案。

   PEG 解析器
     基于 Parsing Expression Grammar 的语法分析器（3.9+），
     取代了旧的 LL(1) 解析器。

   Tokenizer
     词法分析器，将 Python 源文件分解为 Token 流。

   AST (抽象语法树)
     解析器输出的树形中间表示，编译器在此基础上生成符号表和字节码。

   分代 GC (Generational GC)
     CPython 的循环引用回收机制。对象分为 3 代，越老的对象扫描频率越低。

   pymalloc
     CPython 的小块内存分配器（< 256 字节），基于 arena + pool 架构。

   PyModuleDef
     定义 C 扩展模块的元数据结构体，包含模块名、方法表、GC 回调。

   ModuleSpec
     模块规格说明，包含 loader 和来源路径，是 import 系统的核心数据结构。

   BuiltinImporter
     ``sys.meta_path`` 中的第一个 finder，负责查找编译进解释器的内置模块。

   FrozenImporter
     ``sys.meta_path`` 中的第二个 finder，负责查找冻结模块。

   PathFinder
     ``sys.meta_path`` 中的第三个 finder，在 ``sys.path`` 中查找模块文件。

   描述符协议 (descriptor protocol)
     ``__get__`` / ``__set__`` / ``__delete__`` 方法约束。
     ``property``、``classmethod``、``staticmethod`` 都是描述符。

   MRO (Method Resolution Order)
     方法解析顺序（C3 线性化），决定 ``super()`` 和属性查找的顺序。

   Limited API
     C API 的子集，通过 ``#define Py_LIMITED_API`` 启用，保证跨版本兼容。

   Stable ABI
     Limited API 的二进制接口。同一个 ``.so`` 可在多个 CPython 版本上运行。

   PyConfig
     Python 3.8+ 的统一解释器初始化配置结构。

   ceval
     核心评估循环（``Python/ceval.c``），执行字节码的主循环。

   Vectorcall
     PEP 590 定义的快速调用约定（C API 层）。

   co_exceptiontable
     ``PyCodeObject`` 中的异常处理表，记录了 ``try``/``except`` 块的
     范围和跳转目标。
