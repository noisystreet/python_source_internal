CPython 源码架构总览
=====================

本文档描述 CPython 解释器的整体架构与核心子系统，作为源码解读的索引地图。

目标与非目标
------------

**目标**

* 梳理 CPython 主版本（3.x）的核心实现机制
* 为每个子系统提供「高层理解 → 关键结构 → 流程拆解」的渐进式解读
* 配套可运行的示例脚本，验证和演示文档所述机制

**非目标**

* 不做逐行注释翻译式的代码解读
* 不覆盖 CPython 标准库的全部模块（聚焦解释器核心而非纯 Python 库）
* 不替代 CPython 官方文档

分层架构概览
------------

.. mermaid::

   graph TD
       subgraph 应用层
           Bytecode["Python 字节码<br/>(由 py_compile 或交互式编译产生)"]
       end
       subgraph 编译层
           Compiler["编译器 / 语法 & 符号分析<br/>Parser / Compiler / Symtable"]
       end
       subgraph 执行层
           CEval["字节码执行引擎<br/>ceval.c (核心解释循环)"]
       end
       subgraph 运行时支撑层
           Runtime["运行时支撑系统<br/>对象模型 / 内存管理 / 异常 / 模块"]
       end
       subgraph 系统层
           Sys["底层基础抽象层<br/>多线程(GIL) / I/O / 系统调用"]
       end

       Bytecode --> Compiler
       Compiler --> CEval
       CEval --> Runtime
       Runtime --> Sys

核心子系统
----------

1. 对象模型 (Objects/)
    * ``PyObject`` 与 ``PyTypeObject`` 结构
    * 引用计数与垃圾回收
    * 内置类型实现（int、str、dict、list 等）
    * 描述符协议与属性访问

2. 字节码执行引擎 (Python/ceval.c)
    * 解释循环主流程
    * 核心字节码指令分析
    * 调用约定的实现

3. 内存管理 (Objects/obmalloc.c)
    * 小块内存分配（arena / pool / block）
    * 垃圾回收分代机制
    * 环形引用检测

4. 编译系统 (Python/ 编译器前端)
    * Tokenizer → Parser → AST → 符号表 → 字节码
    * 编译器优化（peephole）
    * 导入机制与模块缓存

5. 多线程与并发
    * GIL 设计与实现
    * 线程安全与同步原语
    * async/await 底层实现

6. 异常与调试
    * 异常处理链（try / except / finally）
    * Traceback 对象与栈展开
    * sys.settrace / sys.setprofile 机制

代码仓库对应关系
----------------

CPython 源码布局与本项目的文档映射：

.. list-table::
   :header-rows: 1

   * - CPython 目录
     - 本项目文档
     - 说明
   * - ``Include/``
     - ``docs/objects/``
     - C 头文件定义的结构与宏
   * - ``Objects/``
     - ``docs/objects/``
     - 内置对象的 C 实现
   * - ``Python/``
     - ``docs/compiler/``, ``docs/ceval/``
     - 编译器与执行引擎
   * - ``Parser/``
     - ``docs/compiler/``
     - 语法分析器

获取 CPython 源码
------------------

本项目的解读均基于 CPython 3.14.x。建议在本地克隆一份源码，方便对照阅读：

.. code-block:: bash

    # 在当前项目根目录下执行
    git clone -b v3.14.5 https://github.com/python/cpython.git

设置 ``CPYTHON_SRC`` 环境变量指向该目录后，示例脚本可通过该变量引用 C 头文件：

.. code-block:: bash

    export CPYTHON_SRC=$PWD/cpython

开放决策
--------

* 解读基线版本：CPython 3.14.x
* 文档语言：中文为主，关键术语保留英文原文
* 示例脚本风格：自包含、可独立运行，优先使用 ``ctypes`` 而非 C 扩展
