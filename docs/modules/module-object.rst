模块对象与命名空间 — PyModuleObject
============================================

Python 的模块在 C 层就是 ``PyModuleObject``——一个包装了字典的对象。

从一道题开始
------------

.. code-block:: python

    import math
    math.__dict__  # 模块的命名空间字典

模块的本质是：**一个 ``__dict__`` 字典 + 一些元数据** 。

第一问：PyModuleObject 的结构
-----------------------------

.. code-block:: c

    typedef struct PyModuleObject {
        PyObject_HEAD
        PyObject *md_dict;      // 模块的命名空间字典
        PyObject *md_name;      // 模块名（如 "math"）
        PyObject *md_def;       // 模块定义（扩展模块用）
        void *md_state;         // 模块状态（多阶段初始化用）
        PyObject *md_weaklist;  // 弱引用列表
    } PyModuleObject;

第二问：模块的创建
------------------

.. code-block:: c

    PyObject *PyModule_NewObject(PyObject *name)
    {
        PyModuleObject *m = PyObject_GC_New(PyModuleObject, &PyModule_Type);
        m->md_dict = PyDict_New();
        m->md_name = name;
        return (PyObject *)m;
    }

通过示例脚本验证
----------------

运行 :file:`examples/module_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 模块的本质是什么？
     - PyModuleObject + __dict__ 命名空间字典
   * - __dict__ 的作用？
     - 存储模块的所有属性和函数
