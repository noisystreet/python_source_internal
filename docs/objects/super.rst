.. _objects-super:

super() 的底层实现 — MRO 与方法解析
============================================

.. epigraph::

   "The shortest path between two truths in the real domain passes through the complex domain."

   -- Jacques Hadamard


``super()`` 是 Python 中处理 **协作多继承** （cooperative multiple inheritance）的关键机制。
在 C 层， ``super()`` 返回一个 ``super`` 对象，它根据 MRO（方法解析顺序）委托方法调用。

从一道题开始
------------

.. code-block:: python

    class A:
        def f(self): return "A"

    class B(A):
        def f(self): return super().f() + "B"

    B().f()  # "AB"

``super().f()`` 是怎么找到 ``A.f`` 的？它和 ``self.f`` 的区别在哪？

第一问：super 对象的结构
------------------------

.. code-block:: c

    // Objects/typeobject.c
    typedef struct {
        PyObject_HEAD
        PyTypeObject *type;          // 当前类
        PyObject *obj;               // 当前实例（self）
        PyTypeObject *obj_type;      // obj 的实际类型
    } superobject;

``super()`` 的核心就是三个指针：

- ``type`` ：你在哪个类中调用了 ``super()`` （即包含 ``super()`` 的类）
- ``obj`` ：当前实例（ ``self`` ）
- ``obj_type`` ：实例的实际类型（ ``type(self)`` ）

第二问：属性查找过程
-----------------------

当你调用 ``super().f()`` 时，CPython 执行以下步骤：

.. mermaid::

    flowchart TD
        call["super().f()"] --> lookup["super.__getattribute__('f')"]
        lookup --> mro["获取 obj_type 的 MRO 列表"]
        mro --> skip["跳过 MRO 中 type 之前的类"]
        skip --> find["在 type 之后的类中查找 'f'"]
        find --> result["返回找到的方法描述符"]

C 层实现：

.. code-block:: c

    // Objects/typeobject.c — super_getattro
    static PyObject *
    super_getattro(PyObject *self, PyObject *name)
    {
        superobject *su = (superobject *)self;

        // 1. 获取实例类型的 MRO
        PyObject *mro = su->obj_type->tp_mro;

        // 2. 找到 type 在 MRO 中的位置
        Py_ssize_t i = PySequence_Index(mro, (PyObject *)su->type);

        // 3. 从 type 之后开始查找
        for (i++; i < PyTuple_GET_SIZE(mro); i++) {
            PyTypeObject *base = (PyTypeObject *)PyTuple_GET_ITEM(mro, i);
            descr = _PyType_Lookup(base, name);
            if (descr) {
                return descr_get(descr, su->obj, su->obj_type);
            }
        }

        // 4. 没找到 → 属性错误
        return PyErr_Format(PyExc_AttributeError, ...);
    }

第三问：为什么 super() 不需要传参（3.14+）
------------------------------------------

在 CPython 3.14 中， ``super()`` 在无参数时会自动推断类和方法：

.. code-block:: c

    // Python 编译器在处理 super() 时插入的代码
    // 等价于：
    __class__ = ...  // 编译器自动创建 __class__
    super(__class__, self)

字节码层面， ``super()`` 被展开为对 ``__class__`` cell 变量和 ``self`` 的引用。

通过示例脚本验证
----------------

运行 :file:`examples/super_demo.py`：

.. code-block:: text

    --- MRO 解析 ---
    D.mro() = [D, B, C, A, object]

    --- super 的查找路径 ---
    D().f() → B.f → super() → C.f → super() → A.f

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - super 对象存了什么？
     - type（当前类）+ obj（实例）+ obj_type（实例类型）
   * - super 怎么找方法？
     - 在 MRO 中跳过当前类，从下一个类开始查找
   * - 无参 super() 怎么工作？
     - 编译器自动传入 __class__ 和 self

参考资料
--------

- :ref:`objects-typeobject` — 类型对象与 MRO
- :ref:`objects-descriptor` — 属性查找链中的描述符
- :file:`Objects/typeobject.c` — super 实现
- :pep:`3135` — New Super
