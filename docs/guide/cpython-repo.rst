.. _guide-repo:

CPython 源码仓库导览 — 布局、构建与导航
=================================================

.. epigraph::

   "The map is not the territory."

   -- Alfred Korzybski (on navigating a codebase)


本文是 CPython 源码仓库的 **实操导览** ，面向第一次打开 CPython 源码树的开发者。
上一节 :doc:`/ARCHITECTURE` 讲述了运行时架构，这一节关注仓库本身——文件在哪、
怎么构建、怎么找代码、怎么调试。

.. mermaid::

    flowchart TD
        subgraph Repo["cpython/ 仓库顶层"]
            Include["Include/<br/>C 头文件"]
            Objects["Objects/<br/>内置对象实现"]
            Python["Python/<br/>执行引擎 & 编译器"]
            Parser["Parser/<br/>词法 & 语法分析"]
            Modules["Modules/<br/>内置 C 扩展"]
            Lib["Lib/<br/>标准库 (.py)"]
            Programs["Programs/<br/>入口函数"]
            Doc["Doc/<br/>官方文档 (.rst)"-m]
        end

第一问：仓库目录结构
--------------------

CPython 仓库的顶层目录（排除 `Doc/`、`Tools/` 等辅助目录）：

.. list-table::
   :header-rows: 1

   * - 目录
     - 本项目的文档映射
     - 说明
   * - ``Include/``
     - :doc:`/objects/index`
     - C 头文件。 ``object.h`` （PyObject）、 ``cpython/`` （内部 API）
   * - ``Objects/``
     - :doc:`/objects/index`
     - 内置对象的 C 实现。 ``object.c`` 、 ``longobject.c`` 、 ``dictobject.c`` 等
   * - ``Python/``
     - :doc:`/ceval/index`, :doc:`/compiler/compiler`
     - 解释器核心。 ``ceval.c`` （执行引擎）、 ``compile.c`` （编译器）
   * - ``Parser/``
     - :doc:`/compiler/tokenizer`, :doc:`/compiler/parser`
     - 词法分析器（ ``lexer/`` ）和 PEG 语法分析器（ ``pegen.c`` ）
   * - ``Modules/``
     - :doc:`/modules/index`
     - 内置 C 扩展模块。 ``_sqlite`` 、 ``_ssl`` 、 ``_json`` 等
   * - ``Lib/``
     - 不在本项目范围内
     - Python 标准库。 ``os.py`` 、 ``json/`` 、 ``asyncio/`` 等
   * - ``Programs/``
     - :doc:`/runtime/lifecycle`
     - 入口函数。 ``python.c`` （ ``main()`` ）
   * - ``Mac/``, ``PC/``
     - 不覆盖
     - 平台特定代码（macOS、Windows）

关键文件索引：

.. list-table::
   :header-rows: 1

   * - 文件
     - 作用
   * - ``Include/object.h``
     - PyObject / PyVarObject 定义，引用计数宏
   * - ``Include/cpython/code.h``
     - PyCodeObject 结构（字节码 + 异常表）
   * - ``Objects/object.c``
     - PyObject 基础操作（类型分配、INCREF/DECREF）
   * - ``Objects/typeobject.c``
     - PyTypeObject 实现（MRO、描述符、属性访问）
   * - ``Python/ceval.c``
     - Tier 1 + Tier 2 解释循环
   * - ``Python/compile.c``
     - AST → 字节码
   * - ``Python/pylifecycle.c``
     - 解释器初始化和终结
   * - ``Python/ceval_gil.c``
     - GIL 的 take / drop 实现
   * - ``Python/gc.c``
     - 分代垃圾回收
   * - ``Parser/pegen.c``
     - PEG 解析器入口

第二问：构建系统
------------------

CPython 使用 **autoconf + make** 构建系统。核心命令：

.. code-block:: bash

    # 标准构建
    ./configure --with-pydebug    # 调试构建（推荐用于开发）
    make -j$(nproc)

    # 特殊构建
    ./configure --disable-gil     # 自由线程（无 GIL）实验
    ./configure --enable-optimizations  # PGO 优化（慢，适合发布）

    # 运行
    ./python                     # 使用刚构建的解释器

重要的 `configure` 选项：

.. list-table::
   :header-rows: 1

   * - 选项
     - 用途
   * - ``--with-pydebug``
     - 启用断言、额外检查、 ``--with-pydebug`` 构建
   * - ``--disable-gil``
     - 自由线程（实验性，3.13+）
   * - ``--enable-optimizations``
     - PGO + LTO 优化（构建慢 2-3 倍）
   * - ``--with-valgrind``
     - Valgrind 支持，检测内存泄漏
   * - ``--with-address-sanitizer``
     - AddressSanitizer 支持

构建产物：

.. code-block:: text

    cpython/
    ├── python               # 解释器可执行文件
    ├── libpython3.14d.a     # 静态库（调试构建）
    ├── Modules/
    │   └── *.cpython-314d-*.so  # C 扩展 .so
    └── build/
        └── lib.linux-*-3.14d/   # 编译中间文件

第三问：如何找到正确的代码文件
------------------------------

根据你观察到的 Python 行为反推源码文件：

**情形 1：看到错误消息**

.. code-block:: text

    TypeError: can only concatenate str (not "int") to str

→ ``Objects/unicodeobject.c`` 中搜索 ``can only concatenate``

**情形 2：关心某个内置类型的操作**

.. code-block:: text

    list.append(x)     → Objects/listobject.c → list_append()
    dict["key"]        → Objects/dictobject.c → PyDict_GetItem()
    "hello".upper()    → Objects/unicodeobject.c → unicode_upper()

**情形 3：关心语法或编译行为**

.. code-block:: text

    import foo          → Python/import.c → builtin___import__()
    def f(): ...        → Python/symtable.c → 符号表分析
    try: ... except:    → Python/compile.c → compiler_try_except()

**情形 4：关心运行时行为**

.. code-block:: text

    线程切换            → Python/ceval_gil.c → take_gil() / drop_gil()
    内存分配            → Objects/obmalloc.c → PyObject_Malloc()
    垃圾回收            → Python/gc.c → gc_collect_main()

第四问：调试与诊断
------------------

**调试构建**

``--with-pydebug`` 会启用：

- 所有断言（ ``assert`` ）
- 引用计数调试（追踪未释放的对象）
- ``sys.gettotalrefcount()`` 函数
- 额外的运行时检查

**运行时环境变量**

.. list-table::
   :header-rows: 1

   * - 变量
     - 作用
   * - ``PYTHONDEVMODE=1``
     - 开发模式：启用断言、默认警告
   * - ``PYTHONMALLOC=debug``
     - 调试内存分配器（检测缓冲溢出）
   * - ``PYTHONASYNCIODEBUG=1``
     - asyncio 调试
   * - ``PYTHONTRACEMALLOC=10``
     - 追踪内存分配来源

**GDB 调试**

.. code-block:: bash

    gdb --args ./python script.py

    # 常用断点
    (gdb) b PyObject_Malloc     # 内存分配
    (gdb) b _PyEval_EvalFrameDefault  # 字节码执行开头
    (gdb) b take_gil            # GIL 获取
    (gdb) b drop_gil            # GIL 释放
    (gdb) b gc_collect_main     # GC 触发

    # Python 级别的 GDB 命令
    (gdb) py-bt                 # 打印 Python traceback
    (gdb) py-list               # 查看当前 Python 行
    (gdb) py-print varname      # 打印 Python 变量

第五问：测试套件
------------------

.. code-block:: bash

    # 运行全部测试
    ./python -m test

    # 运行单个测试文件
    ./python -m test test_list   # Lib/test/test_list.py

    # 运行单个测试用例
    ./python -m test test_list -m TestList.test_append

    # 测试 C 扩展模块
    ./python -m test test_capi

    # 性能测试
    ./python -m test.bench

.. note::

   CPython 的测试套件非常庞大（数千个测试文件）。开发时通常只运行相关的单文件测试，
   最后提交前再跑全局测试。

第六问：.pyc 编译流程速查
--------------------------

从 ``.py`` 到执行的完整文件流动：

.. mermaid::

    flowchart LR
        py["source.py"] -->|"第一次导入"| parser["Parser/pegen.c<br/>PEG 解析"]
        parser --> ast["AST (Python-ast.c)"]
        ast --> symtable["Python/symtable.c<br/>符号表"]
        symtable --> compiler["Python/compile.c<br/>编译器"]
        compiler --> pyc["__pycache__/source.cpython-314.pyc"]
        pyc -->|"后续导入"| load["Python/marshal.c<br/>反序列化"]
        load --> code["PyCodeObject"]
        code --> ceval["Python/ceval.c<br/>执行"]

    py -->|"直接运行"| compile["builtins.compile()"]
    compile --> code

通过示例脚本验证
----------------

本仓库的配套示例脚本覆盖了大多数子系统，可以通过冒烟测试一次性验证：

.. code-block:: bash

    make test      # 运行 41 个示例脚本
    make lint      # 代码检查
    make docs      # 构建 HTML 文档

运行 :file:`examples/hello_pyobject.py` 是最简单的入门示例。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 核心目录有哪些？
     - Include/（头文件）、Objects/（对象实现）、Python/（引擎）、Parser/（解析器）
   * - 怎么构建？
     - ``./configure --with-pydebug && make -j``
   * - 怎么找代码入口？
     - 根据错误消息反向搜索，或按类型/操作名查找
   * - 怎么调试？
     - ``--with-pydebug`` + ``gdb`` + ``PYTHONDEVMODE``
   * - 怎么运行测试？
     - ``./python -m test test_xxx``
   * - .py 到执行的完整链路？
     - Parser → AST → 符号表 → 编译器 → .pyc → ceval

参考资料
--------

- :file:`README.rst` — CPython 官方 README
