CPython 源码架构总览
=====================

本文档描述 CPython 3.14 解释器的整体架构与核心子系统，作为整套源码解读的**索引地图** 。
每个子系统的索引页包含该子系统全部章节的入口链接。

目标与非目标
------------

**目标**

* 梳理 CPython 3.14 的核心实现机制
* 为每个子系统提供「高层理解 → 关键结构 → 流程拆解」的渐进式解读
* 配套可运行的示例脚本，验证和演示文档所述机制

**非目标**

* 不做逐行注释翻译式的代码解读
* 不覆盖 CPython 标准库的全部模块（聚焦解释器核心而非纯 Python 库）
* 不替代 CPython 官方文档

从源码到执行：完整数据流
------------------------

.. mermaid::

    flowchart LR
        py["source.py"] --> tokenizer["Tokenizer<br/>Parser/lexer/"]
        tokenizer --> parser["PEG Parser<br/>Parser/pegen.c"]
        parser --> ast["AST<br/>Python-ast.c"]
        ast --> symtable["Symtable<br/>Python/symtable.c"]
        symtable --> compiler["Compiler<br/>Python/compile.c"]
        compiler --> bc["PyCodeObject<br/>（字节码 + 异常表）"]
        bc --> ceval["ceval<br/>Python/ceval.c"]
        ceval --> result["执行结果"]
        ceval --> objects["PyObject<br/>对象系统支撑"]

子系统索引
----------

.. list-table::
   :header-rows: 1

   * - 子系统
     - 章节数
     - 核心源码路径
     - 入口
   * - 对象模型
     - 13
     - ``Include/``, ``Objects/``
     - :doc:`objects/index`
   * - 字节码执行引擎
     - 6
     - ``Python/ceval.c``
     - :doc:`ceval/index`
   * - 内存管理
     - 4
     - ``Objects/obmalloc.c``, ``Python/gc.c``
     - :doc:`gc/index`
   * - 编译系统
     - 6
     - ``Parser/``, ``Python/compile.c``
     - :doc:`compiler/index`
   * - 并发与并行
     - 4
     - ``Python/ceval_gil.c``
     - :doc:`concurrency/index`
   * - 异常与调试
     - 4
     - ``Python/errors.c``, ``Python/ceval.c``
     - :doc:`exceptions/index`
   * - 模块系统
     - 3
     - ``Python/import.c``, ``Objects/moduleobject.c``
     - :doc:`modules/index`
   * - 扩展与 C API
     - 7
     - ``Include/``, ``Python/modsupport.c``
     - :doc:`extensions/index`
   * - 运行时系统
     - 6
     - ``Python/pylifecycle.c``, ``Python/pystate.c``
     - :doc:`runtime/index`

关键数据结构交叉索引
--------------------

下面列出 CPython 最核心的数据结构，以及它们在文档中的位置。

.. list-table::
   :header-rows: 1

   * - 结构名
     - 所在头文件
     - 说明
     - 文档入口
   * - ``PyObject``
     - ``Include/object.h``
     - 所有 Python 对象的基类（ob_refcnt + ob_type）
     - :doc:`objects/pyobject`
   * - ``PyTypeObject``
     - ``Include/object.h``
     - 类型对象，决定对象行为（tp_* 函数指针表）
     - :doc:`objects/typeobject`
   * - ``_PyInterpreterFrame``
     - ``Include/internal/pycore_interpframe_structs.h``
     - 函数调用的帧（instr_ptr / stackpointer / localsplus）
     - :doc:`ceval/ceval-loop`
   * - ``PyCodeObject``
     - ``Include/cpython/code.h``
     - 编译产物：字节码 + 常量 + 异常表
     - :doc:`compiler/compiler`
   * - ``struct tok_state``
     - ``Parser/lexer/state.h``
     - Tokenizer 状态：缓冲区 / 缩进栈 / f-string 模式栈
     - :doc:`compiler/tokenizer`
   * - ``struct symtable``
     - ``Include/internal/pycore_symtable.h``
     - 符号表：作用域与名字绑定
     - :doc:`compiler/symtable`
   * - ``PyGC_Head``
     - ``Include/internal/pycore_gc.h``
     - GC 链表节点（嵌入在容器对象中）
     - :doc:`gc/gc`
   * - ``struct _gil_runtime_state``
     - ``Python/ceval_gil.c``
     - GIL 状态：locked / cond / interval
     - :doc:`concurrency/gil`
   * - ``PyThreadState``
     - ``Include/cpython/pystate.h``
     - 线程状态：当前帧 / 异常 / GIL 计数
     - :doc:`runtime/thread-state`
   * - ``PyInterpreterState``
     - ``Include/internal/pycore_interp.h``
     - 解释器状态：模块缓存 / GC / Unicode / int 池
     - :doc:`runtime/interpreter-state`

CPython 源码布局与本项目文档的映射
-----------------------------------

.. list-table::
   :header-rows: 1

   * - CPython 目录
     - 本项目文档
     - 说明
   * - ``Include/object.h``, ``Include/cpython/``
     - :doc:`objects/pyobject`, :doc:`objects/typeobject`
     - 对象系统 C 头文件定义
   * - ``Objects/``
     - :doc:`objects/index`
     - 内置对象的 C 实现
   * - ``Python/ceval.c``
     - :doc:`ceval/index`
     - 字节码执行引擎
   * - ``Python/compile.c``, ``Python/symtable.c``
     - :doc:`compiler/compiler`, :doc:`compiler/symtable`
     - 编译器后端
   * - ``Parser/``
     - :doc:`compiler/tokenizer`, :doc:`compiler/parser`
     - 词法 & 语法分析器
   * - ``Python/gc.c``, ``Objects/obmalloc.c``
     - :doc:`gc/index`
     - 内存管理与垃圾回收
   * - ``Python/ceval_gil.c``
     - :doc:`concurrency/gil`
     - GIL 实现
   * - ``Python/errors.c``
     - :doc:`exceptions/exception-handling`
     - 异常处理机制
   * - ``Python/pylifecycle.c``, ``Python/pystate.c``
     - :doc:`runtime/index`
     - 运行时生命周期

示例脚本索引
------------

所有示例脚本位于 :file:`examples/` 目录，可以通过冒烟测试一次性运行：

.. code-block:: bash

    make test      # 运行全部 39 个示例脚本
    make lint      # ruff + mypy 代码检查
    make docs      # 构建 HTML 文档

各子系统对应的示例脚本：

.. list-table::
   :header-rows: 1

   * - 子系统
     - 示例脚本
   * - 对象模型
     - ``pyobject_layout.py``, ``refcount_demo.py``, ``typeobject_demo.py``, ``function_code_demo.py``, ``iterator_generator_demo.py``, ``weakref_demo.py``, ``longobject_demo.py``, ``unicode_demo.py``, ``dict_demo.py``, ``list_demo.py``, ``tuple_set_demo.py``, ``descriptor_demo.py``
   * - 字节码执行引擎
     - ``ceval_loop_demo.py``, ``bytecodes_demo.py``, ``calls_demo.py``, ``specialize_demo.py``, ``tier2_demo.py``, ``jit_demo.py``
   * - 内存管理
     - ``obmalloc_demo.py``, ``gc_demo.py``, ``gc_cycles_demo.py``, ``arena_demo.py``
   * - 编译系统
     - ``tokenizer_demo.py``, ``parser_demo.py``, ``ast_demo.py``, ``symtable_demo.py``, ``compiler_demo.py``, ``import_demo.py``
   * - 并发与并行
     - ``gil_demo.py``, ``async_demo.py``
   * - 异常与调试
     - ``exception_demo.py``, ``traceback_demo.py``, ``tracing_demo.py``, ``debug_demo.py``
   * - 模块系统
     - ``module_demo.py``, ``sysmodules_demo.py``
   * - 运行时系统
     - ``marshal_demo.py``, ``codecs_demo.py``

获取 CPython 源码
------------------

本项目的解读均基于 CPython 3.14.x。建议在本地克隆一份源码，方便对照阅读：

.. code-block:: bash

    git clone -b v3.14.5 https://github.com/python/cpython.git

设置 ``CPYTHON_SRC`` 环境变量指向该目录后，示例脚本可通过该变量引用 C 头文件：

.. code-block:: bash

    export CPYTHON_SRC=$PWD/cpython

开放决策
--------

* 解读基线版本：CPython 3.14.x
* 文档语言：中文为主，关键术语保留英文原文
* 示例脚本风格：自包含、可独立运行，优先使用 ``ctypes`` 而非 C 扩展
