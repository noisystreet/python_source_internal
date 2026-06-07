内置模块 — 解释器自带的模块
====================================

CPython 有一些模块是**编译进解释器**的，不需要从文件加载。

第一问：内置模块列表
--------------------

内置模块定义在 :file:`Python/config.c` 中：

.. code-block:: c

    struct _inittab _PyImport_Inittab[] = {
        {"sys", PyInit_sys},
        {"builtins", PyInit_builtins},
        {"_thread", PyInit__thread},
        // ...
    };

第二问：内置模块的导入
----------------------

内置模块的 finder（``BuiltinImporter``）直接检查 ``_PyImport_Inittab`` 表。
找到后调用对应的 ``PyInit_*`` 函数初始化模块。

通过示例脚本验证
----------------

运行 :file:`examples/module_demo.py` 可以查看已加载的内置模块。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 内置模块有哪些？
     - sys, builtins, _thread 等，定义在 _PyImport_Inittab
   * - 内置模块的查找？
     - BuiltinImporter 直接查表，不走文件系统
   * - 初始化方式？
     - 调用 PyInit_* 函数
