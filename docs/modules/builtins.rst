内置模块与导入管道 — import 的底层实现
==============================================

CPython 有一些模块是**编译进解释器**的，不需要从文件加载。
除此之外，还有**冻结模块**（frozen modules）和基于文件的加载。
这一节梳理整个导入管道（import pipeline）。

从一道题开始
------------

.. code-block:: python

    import sys
    import math       # 从文件加载
    import _thread    # 内置模块

这三个 ``import`` 走的是三条不同的路径。CPython 通过统一的 **finder/loader 协议**
将这三条路径串联起来。

第一问：sys.meta_path 与 finder/loader 协议
--------------------------------------------

Python 的导入机制基于 ``sys.meta_path`` ——一个 finder 列表：

.. code-block:: python

    >>> import sys
    >>> sys.meta_path
    [BuiltinImporter, FrozenImporter, PathFinder]

每个 finder 按序尝试查找模块：

.. mermaid::

    flowchart TD
        import["import math"] --> meta_path["遍历 sys.meta_path"]
        meta_path --> builtin["1. BuiltinImporter<br/>find_spec('math')"]
        builtin --> found1{"找到?"}
        found1 -->|"是"| load1["loader.exec_module()"]
        found1 -->|"否"| frozen["2. FrozenImporter<br/>find_spec('math')"]
        frozen --> found2{"找到?"}
        found2 -->|"是"| load2["loader.exec_module()"]
        found2 -->|"否"| path["3. PathFinder<br/>在 sys.path 中查找"]
        path --> found3{"找到?"}
        found3 -->|"是"| load3["loader.exec_module()"]
        found3 -->|"否"| error["ModuleNotFoundError"]

**核心技术：** 每个 finder 返回一个 ``ModuleSpec`` （模块规格说明），其中包含
loader 和其他元数据。loader 负责实际的加载和执行。

.. code-block:: c

    // 模块规格说明的结构（简化）
    typedef struct {
        PyObject *name;         // 模块名
        PyObject *loader;       // 加载器对象
        PyObject *origin;       // 来源路径
        int submodule_search_locations; // 子模块搜索路径
    } ModuleSpec;

第二问：BuiltinImporter — 内置模块
----------------------------------

内置模块在编译时注册到 ``_PyImport_Inittab`` 数组中：

.. code-block:: c

    // Python/config.c
    extern PyObject *PyInit_sys(void);
    extern PyObject *PyInit_builtins(void);
    extern PyObject *PyInit__thread(void);

    struct _inittab _PyImport_Inittab[] = {
        {"sys", PyInit_sys},
        {"builtins", PyInit_builtins},
        {"_thread", PyInit__thread},
        {"_io", PyInit__io},
        {"_json", PyInit__json},
        // ... 约 30 个内置模块
        {NULL, NULL}  // 哨兵
    };

BuiltinImporter 的 ``find_spec`` 实现很简单——查表：

.. code-block:: c

    // Python/import.c
    PyObject *BuiltinImporter_find_spec(PyObject *self, PyObject *name) {
        for (int i = 0; _PyImport_Inittab[i].name != NULL; i++) {
            if (strcmp(_PyImport_Inittab[i].name, name) == 0) {
                // 找到，创建 ModuleSpec
                return create_spec(name, BUILTIN);
            }
        }
        Py_RETURN_NONE;  // 未找到
    }

第三问：FrozenImporter — 冻结模块
----------------------------------

冻结模块是**编译成 C 数组的字节码**，直接链接进解释器。
``importlib._bootstrap`` 和 ``importlib._bootstrap_external`` 就是
冻结模块——它们在解释器启动前就已经被编译为字节码并嵌入到可执行文件中。

.. code-block:: c

    // Programs/_bootstrap_python.c
    // 冻结模块的 C 表示形式
    struct _frozen {
        const char *name;               // 模块名
        const unsigned char *code;       // marshal 序列化的字节码
        int size;                        // 字节码大小
    };

    // 由 Tools/scripts/freeze_modules.py 生成
    extern const unsigned char _Py_M__importlib_bootstrap[];
    extern const unsigned char _Py_M__importlib_bootstrap_external[];

    static const struct _frozen _PyImport_FrozenModules[] = {
        {"_frozen_importlib", _Py_M__importlib_bootstrap, 0},
        {"_frozen_importlib_external", _Py_M__importlib_bootstrap_external, 0},
        // ...
        {NULL, NULL, 0}  // 哨兵
    };

FrozenImporter 比 BuiltinImporter 稍复杂——它需要反序列化字节码并执行：

.. code-block:: c

    // Python/import.c 中 FrozenImporter 的加载逻辑
    PyObject *FrozenImporter_exec_module(PyObject *spec) {
        // 1. 在 _PyImport_FrozenModules 中查找模块名
        const struct _frozen *p = find_frozen(spec->name);

        // 2. 反序列化字节码
        PyObject *code = marshal_loads(p->code, p->size);

        // 3. 创建模块对象
        PyModuleObject *mod = PyModule_New(spec->name);

        // 4. 在模块的命名空间中执行字节码
        exec(code, mod->md_dict);

        return (PyObject *)mod;
    }

第四问：importlib 的自举
------------------------

``importlib._bootstrap`` 是 CPython 最特殊的模块之一——它是**用 Python 写的
但以冻结模块形式存在**，负责实现 ``sys.meta_path`` 中的 finder 和 loader。

自举流程：

.. mermaid::

    flowchart TD
        init["Py_InitializeFromConfig"] --> ready["_Py_ReadyBuiltins()<br/>加载 builtins/sys/_thread"]
        ready --> frozen["_PyImport_FrozenImport()<br/>加载 _frozen_importlib"]
        frozen --> bootstrap["执行 importlib._bootstrap<br/>注册 BuiltinImporter / FrozenImporter"]
        bootstrap --> ext["加载 importlib._bootstrap_external<br/>注册 PathFinder / FileLoader"]
        ext --> path["sys.path 就绪<br/>现在可以 import 任何模块"]

这个自举过程保证了：在 ``importlib._bootstrap`` 加载之前，
只有 ``BuiltinImporter`` 和 ``FrozenImporter`` 可用——它们是用 C 实现的。

通过示例脚本验证
----------------

运行 :file:`examples/module_demo.py` 和 :file:`examples/import_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 内置模块存在哪？
     - _PyImport_Inittab 表（编译进解释器）
   * - 冻结模块是什么？
     - 字节码编译为 C 数组，链接进可执行文件
   * - BuiltinImporter 怎么工作？
     - 查 _PyImport_Inittab 表，调用 PyInit_*
   * - FrozenImporter 怎么工作？
     - 查 _PyImport_FrozenModules 表，marshal 反序列化后 exec
   * - importlib 怎么自举？
     - C 层先加载 _frozen_importlib，然后它注册各类 finder/loader
   * - sys.meta_path 的顺序？
     - BuiltinImporter → FrozenImporter → PathFinder
