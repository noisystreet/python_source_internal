.. _extensions-dynamic-loading:

动态加载机制 — .so / .pyd 的加载
==========================================

.. epigraph::

   "All the world's a stage, and all the men and women merely players; They have their exits and their entrances."

   -- William Shakespeare, As You Like It (on loading and unloading)


CPython 通过 ``dlopen`` （Linux）或 ``LoadLibrary`` （Windows）加载 C 扩展。
这个机制是 CPython "导入系统" 中 C 扩展模块与传统 .py 模块的分水岭。

从一道题开始
------------

.. code-block:: python

    # 扩展模块的"导入"和普通 .py 模块本质上不同
    import _json       # 内置模块（已编译进解释器）
    import mymodule    # 可能是 .so / .pyd 文件

对于 ``mymodule.so``，导入路径是：**不经过 Python 编译器**。

第一问：加载流程
----------------

.. mermaid::

    flowchart TD
        import["import foo"] --> pathfinder["PathFinder<br/>在 sys.path 中查找"]
        pathfinder --> found{"找到 foo.so?"}
        found -->|"否"| error["ModuleNotFoundError"]
        found -->|"是"| spec["创建 ModuleSpec<br/>loader = ExtensionFileLoader"]
        spec --> dlopen["ExtensionFileLoader.exec_module()"]
        dlopen --> dll["dlopen('foo.so')<br/>加载动态库到进程地址空间"]
        dll --> sym["dlsym(handle, 'PyInit_foo')<br/>查找入口函数"]
        sym --> init["调用 PyInit_foo()"]
        init --> mod["返回 PyModuleObject"]
        mod --> cache["存入 sys.modules"]

关键实现：

.. code-block:: c

    // Python/importdl.c 中的核心逻辑
    PyObject *_PyImport_FindExtensionObject(PyObject *name, PyObject *path) {
        // 1. dlopen 加载 .so
        void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
        if (handle == NULL) {
            PyErr_SetString(PyExc_ImportError, dlerror());
            return NULL;
        }

        // 2. 构造入口函数名: PyInit_<name>
        char init_name[256];
        snprintf(init_name, sizeof(init_name), "PyInit_%s", name);

        // 3. 查找入口函数
        PyObject *(*init_func)(void) = dlsym(handle, init_name);

        // 4. 调用入口函数
        return init_func();
    }

第二问：符号可见性与 RTLD_LOCAL vs RTLD_GLOBAL
------------------------------------------------

.. code-block:: c

    // RTLD_LOCAL（默认）：扩展的符号不导出给其他 .so
    void *handle = dlopen("foo.so", RTLD_NOW | RTLD_LOCAL);

    // RTLD_GLOBAL：扩展的符号全局可见
    void *handle = dlopen("bar.so", RTLD_NOW | RTLD_GLOBAL);

``RTLD_LOCAL`` 是 CPython 的默认选项，避免不同扩展之间的符号冲突。
如果一个扩展依赖另一个扩展中的 C 函数（如 ``numpy`` 依赖 ``_multiarray_umath``），
加载者需要指定 ``RTLD_GLOBAL``。

第三问：Windows 平台的差异
---------------------------

Windows 上使用 ``LoadLibrary`` 和 ``GetProcAddress``：

.. code-block:: c

    // PC/importdl.c
    void *handle = LoadLibraryExW(path, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);

    // 入口函数名在 Windows 上需要处理 dll 导出名问题
    FARPROC init_func = GetProcAddress(handle, "PyInit_foo");

Windows 的关键与 Linux 不同：
- 扩展文件后缀是 ``.pyd``
- 需要 ``__declspec(dllexport)`` 导出 ``PyInit_*``
- ``LOAD_WITH_ALTERED_SEARCH_PATH`` 防止 DDL 劫持

通过示例脚本验证
----------------

运行 :file:`examples/import_demo.py` 观察模块的导入过程。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 怎么加载 C 扩展？
     - ``dlopen`` (Linux) / ``LoadLibrary`` (Windows)
   * - 入口函数是什么？
     - ``PyInit_<模块名>``
   * - dlopen 的 RTLD_LOCAL 和 RTLD_GLOBAL 区别？
     - LOCAL 隔离符号，GLOBAL 导出符号
   * - Windows 和 Linux 的主要区别？
     - .so vs .pyd, LoadLibrary vs dlopen, dllexport 导出

参考资料
--------

- :ref:`compiler-import` — 导入系统的完整流程
- :ref:`modules-object` — 模块对象的创建与初始化
- :file:`Python/importdl.c` — 动态加载实现
