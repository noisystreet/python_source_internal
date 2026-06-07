动态加载机制 — .so / .pyd 的加载
==========================================

CPython 通过 ``dlopen``（Linux）或 ``LoadLibrary``（Windows）加载 C 扩展。

第一问：加载流程
---------------

.. code-block:: text

    import foo
    → PathFinder 找到 foo.so
    → Loader 调用 dlopen("foo.so")
    → 执行模块初始化函数 PyInit_foo()
    → 返回模块对象

第二问：模块初始化函数
-------------------

.. code-block:: c

    PyMODINIT_FUNC PyInit_foo(void) {
        return PyModuleDef_Init(&foo_module);
    }
