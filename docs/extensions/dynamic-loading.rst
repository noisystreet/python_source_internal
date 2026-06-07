动态加载机制 — .so / .pyd 的加载
==========================================

CPython 通过 ``dlopen`` （Linux）或 ``LoadLibrary`` （Windows）加载 C 扩展。

第一问：加载流程
----------------

.. code-block:: text

    import foo
    → PathFinder 找到 foo.so
    → Loader 调用 dlopen("foo.so")
    → 执行模块初始化函数 PyInit_foo()
    → 返回模块对象

第二问：模块初始化函数
----------------------

.. code-block:: c

    PyMODINIT_FUNC PyInit_foo(void) {
        return PyModuleDef_Init(&foo_module);
    }


小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 怎么加载扩展？
     - ``dlopen`` (Linux) / ``LoadLibrary`` (Windows)
   * - 入口函数是什么？
     - ``PyInit_<模块名>``
   * - 模块定义在哪？
     - ``PyModuleDef`` 结构体

通过示例脚本验证
----------------

运行 :file:`examples/import_demo.py` 观察模块的导入过程。

