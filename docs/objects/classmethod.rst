classmethod / staticmethod 的底层实现
===========================================

.. epigraph::

   "The whole is greater than the sum of its parts."

   -- Aristotle, Metaphysics


``classmethod`` 和 ``staticmethod`` 是 Python 内置的描述符类型，
它们修改方法调用时的**第一个参数**传递方式。

从一道题开始
------------

.. code-block:: python

    class C:
        @classmethod
        def f(cls): print(cls)

        @staticmethod
        def g(x): print(x)

    C.f()  # cls = C，自动传入
    C.g(1) # 没有额外参数传入，等价于普通函数

在 C 层，这两个装饰器都返回一个包装对象，通过描述符协议拦截调用。

第一问：classmethod 的结构与调用
--------------------------------

.. code-block:: c

    // Objects/classobject.c
    typedef struct {
        PyObject_HEAD
        PyObject *cm_callable;  // 被包装的函数（如 f）
        PyObject *cm_dict;      // 额外属性字典
    } PyCMethodObject;

当 ``C.f()`` 被调用时，CPython 在 ``C.__dict__`` 中找到 ``PyCMethodObject``：

.. code-block:: c

    static PyObject *
    cm_descr_get(PyObject *self, PyObject *obj, PyObject *type) {
        PyCMethodObject *cm = (PyCMethodObject *)self;

        // 类方法始终将 type（即类本身）作为第一个参数
        // obj 被忽略——即使通过实例调用，传的也是 type
        if (type == NULL)
            type = Py_TYPE(obj);

        // 返回一个 bound_method，将 type 绑定为第一个参数
        return PyMethod_New(cm->cm_callable, type);
    }

关键区别：
- ``classmethod`` 忽略 ``obj``（实例），传递 ``type``（类）作为第一参数
- 即使通过 ``obj.f()`` 调用，传的也是 ``type(obj)`` 而非 ``obj``

第二问：staticmethod 的结构与调用
----------------------------------

.. code-block:: c

    // Objects/classobject.c
    typedef struct {
        PyObject_HEAD
        PyObject *sm_callable;  // 被包装的函数
    } PyStaticMethodObject;

``staticmethod`` 的描述符获取实现极其简单——**直接返回原始函数**：

.. code-block:: c

    static PyObject *
    sm_descr_get(PyObject *self, PyObject *obj, PyObject *type) {
        PyStaticMethodObject *sm = (PyStaticMethodObject *)self;
        // 直接返回原始函数，不进行任何绑定
        Py_INCREF(sm->sm_callable);
        return sm->sm_callable;
    }

这意味着 ``C.g`` 返回的就是 ``g`` 函数本身，和写在外面没有区别。
为什么还要用 ``@staticmethod``？它告诉读者这个方法是与类相关的辅助函数，
即使子类重写也不受影响。

第三问：classmethod 与普通方法的对比
--------------------------------------

.. list-table::
   :header-rows: 1

   * - 特性
     - 普通方法
     - classmethod
     - staticmethod
   * - C 层类型
     - ``PyFunctionObject``
     - ``PyCMethodObject``
     - ``PyStaticMethodObject``
   * - 描述符返回
     - bound method（绑定实例）
     - bound method（绑定类）
     - 原始函数（不绑定）
   * - 第一个参数
     - ``self`` （实例）
     - ``cls`` （类）
     - 无（完全由调用者决定）
   * - 子类调用
     - 传递子类实例
     - 传递子类
     - 无影响

通过示例脚本验证
----------------

运行 :file:`examples/classmethod_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - classmethod 怎么工作？
     - 包装函数，cm_descr_get 将 type 绑定为第一个参数
   * - staticmethod 怎么工作？
     - 包装函数，sm_descr_get 直接返回原始函数
   * - 通过实例调用 classmethod？
     - 传的仍是 type(obj)，不是 obj
   * - staticmethod 和普通函数区别？
     - 本质无区别，语义上属于类的命名空间

参考资料
--------

- :file:`Objects/classobject.c` — classmethod/staticmethod 实现
