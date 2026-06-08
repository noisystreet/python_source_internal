.. _modules-object:

模块对象与命名空间 — PyModuleObject
============================================

.. epigraph::

   "A name is a mirror of the thing it names."

   -- Plato, Cratylus


Python 的模块在 C 层就是 ``PyModuleObject``——一个包装了字典的对象。
C 扩展模块的初始化同样围绕 ``PyModuleDef`` 和 ``PyModuleObject`` 展开。

从一道题开始
------------

.. code-block:: python

    import math
    math.__dict__  # 模块的命名空间字典

模块的本质是：**一个 ``__dict__`` 字典 + 一些元数据**。

.. mermaid::

    flowchart LR
        subgraph PyModuleObject["PyModuleObject"]
            md_dict["md_dict → 命名空间 dict"]
            md_name["md_name → 模块名"]
            md_def["md_def → PyModuleDef（扩展模块）"]
            md_state["md_state → 模块状态指针"]
        end
        md_dict --> keys["math.pi, math.sin, ..."]
        md_def --> methods["PyMethodDef 数组"]
        md_def --> slots["PyModuleDef_Slot 数组"]

第一问：PyModuleObject 的结构
-----------------------------

.. code-block:: c

    typedef struct PyModuleObject {
        PyObject_HEAD
        PyObject *md_dict;      // 模块的命名空间字典（读写属性都存这里）
        PyObject *md_name;      // 模块名（如 "math"）
        PyObject *md_def;       // 模块定义（PyModuleDef * 的包装）
        void *md_state;         // 模块状态指针（多阶段初始化用）
        PyObject *md_weaklist;  // 弱引用列表
    } PyModuleObject;

模块的属性和函数全部存在 ``md_dict`` 中。``math.pi`` 的访问路径是：

.. code-block:: c

    // 等价于 math.__dict__["pi"]
    PyObject *value = PyDict_GetItemString(m->md_dict, "pi");

第二问：纯 Python 模块的创建
----------------------------

``import math`` 时，CPython 为 ``math.py`` 创建一个空模块对象，然后执行
模块代码填充 ``__dict__``：

.. code-block:: c

    // Python/import.c 中的简化流程
    PyObject *create_module(PyObject *spec) {
        // 1. 创建空模块对象
        PyModuleObject *mod = (PyModuleObject *)PyModule_NewObject(spec->name);

        // 2. 设置 __spec__、__name__、__file__ 等元数据
        PyDict_SetItemString(mod->md_dict, "__spec__", spec);
        PyDict_SetItemString(mod->md_dict, "__name__", spec->name);
        PyDict_SetItemString(mod->md_dict, "__file__", spec->origin);

        // 3. 执行模块代码
        exec_module(mod, spec);  // 调用 compile() + exec() 填充 __dict__

        return (PyObject *)mod;
    }

第三问：C 扩展模块的创建（PyModule_Create）
-------------------------------------------

C 扩展模块通过 ``PyModule_Create`` 从 ``PyModuleDef`` 构造模块：

.. code-block:: c

    // Objects/moduleobject.c
    PyObject *PyModule_Create(PyModuleDef *def) {
        // 1. 分配 PyModuleObject
        PyModuleObject *m = (PyModuleObject *)PyModule_NewObject(def->m_name);

        // 2. 设置 md_def
        m->md_def = (PyObject *)def;

        // 3. 注册方法表
        for (PyMethodDef *ml = def->m_methods; ml->ml_name != NULL; ml++) {
            PyObject *func = PyCFunction_New(ml, (PyObject *)m);
            PyDict_SetItemString(m->md_dict, ml->ml_name, func);
        }

        return (PyObject *)m;
    }

``PyModuleDef`` 的结构：

.. code-block:: c

    // 一个典型的模块定义
    static PyModuleDef mymodule = {
        PyModuleDef_HEAD_INIT,  // 头部宏
        "mymodule",             // m_name
        "My module docs",       // m_doc
        -1,                     // m_size（-1 表示无模块状态）
        methods,                // m_methods（PyMethodDef 数组）
        NULL,                   // m_slots（多阶段初始化）
        NULL,                   // m_traverse（GC）
        NULL,                   // m_clear（GC）
        NULL,                   // m_free（析构）
    };

第四问：模块的 GC 跟踪
----------------------

``PyModuleObject`` 是容器对象，需要通过 GC 跟踪其内部的对象引用：

.. code-block:: c

    // Objects/moduleobject.c
    static int module_traverse(PyModuleObject *m, visitproc visit, void *arg) {
        Py_VISIT(m->md_dict);
        Py_VISIT(m->md_def);
        Py_VISIT(m->md_state);
        return 0;
    }

    static int module_clear(PyModuleObject *m) {
        Py_CLEAR(m->md_dict);
        Py_CLEAR(m->md_def);
        Py_CLEAR(m->md_state);
        return 0;
    }

如果 ``__dict__`` 中的对象引用了模块自身（例如模块中的函数引用了模块），
就形成了循环引用。GC 通过 ``module_traverse`` 和 ``module_clear`` 处理这种情况。

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
   * - C 扩展模块怎么定义？
     - 通过 PyModuleDef 结构体，注册 PyMethodDef 方法表
   * - 模块的 GC 怎么处理？
     - module_traverse / module_clear 跟踪容器内的引用
   * - m_size = -1 什么意思？
     - 不需要模块级状态（无 per-module 数据）

参考资料
--------

- :ref:`compiler-import` — 导入系统如何创建模块对象
- :ref:`modules-builtins` — 内置模块与 PyModuleDef
- :file:`Objects/moduleobject.c` — PyModuleObject
