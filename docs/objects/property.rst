property 的底层实现 — PyProperty_Type
=============================================

.. epigraph::

   "Simplicity is prerequisite for reliability."

   -- Edsger Dijkstra


``property`` 是 Python 内置的描述符类型，它将方法调用伪装成属性访问。
在 C 层，``property`` 是 ``PyProperty_Type``——一个实现了描述符协议的类。

从一道题开始
------------

.. code-block:: python

    class C:
        @property
        def x(self):
            return 42

    obj = C()
    obj.x  # 42（没有调用括号）

``obj.x`` 触发的是描述符协议中的 ``__get__`` 方法，而不是普通的函数调用。

第一问：PyPropertyObject 的结构
-------------------------------

.. code-block:: c

    // Objects/descrobject.c
    typedef struct {
        PyObject_HEAD
        PyObject *prop_get;    // fget — getter 函数
        PyObject *prop_set;    // fset — setter 函数
        PyObject *prop_del;    // fdel — deleter 函数
        PyObject *prop_doc;    // __doc__ 字符串
        int getter_descriptors; // 缓存标记
    } PyPropertyObject;

``@property`` 的本质就是将 ``prop_get``、``prop_set``、``prop_del`` 三个
函数指针打包到一个对象中。

第二问：property 的描述符协议
-------------------------------

``PyProperty_Type`` 实现了 ``tp_descr_get`` 和 ``tp_descr_set``：

.. code-block:: c

    // Objects/descrobject.c
    static PyObject *
    property_descr_get(PyObject *self, PyObject *obj, PyObject *type) {
        PyPropertyObject *prop = (PyPropertyObject *)self;

        if (prop->prop_get == NULL) {
            PyErr_SetString(PyExc_AttributeError, "unreadable attribute");
            return NULL;
        }

        // 调用 fget(self)
        return PyObject_CallOneArg(prop->prop_get, obj);
    }

    static int
    property_descr_set(PyObject *self, PyObject *obj, PyObject *value) {
        PyPropertyObject *prop = (PyPropertyObject *)self;

        if (value == NULL) {
            // 删除属性 → 调用 fdel
            if (prop->prop_del == NULL) {
                PyErr_SetString(PyExc_AttributeError, "can't delete attribute");
                return -1;
            }
            return PyObject_CallOneArg(prop->prop_del, obj);
        }

        // 设置属性 → 调用 fset
        if (prop->prop_set == NULL) {
            PyErr_SetString(PyExc_AttributeError, "can't set attribute");
            return -1;
        }
        return PyObject_CallOneArg(prop->prop_set, obj);
    }

当 ``obj.x`` 被解析时，CPython 在 ``C.__dict__`` 中找到 ``x`` 这个
``PyPropertyObject``，发现它有 ``tp_descr_get``，于是调用 ``property_descr_get``。

第三问：property 的装饰器语法
------------------------------

.. code-block:: python

    @property
    def x(self): ...

等价于 ``x = property(x)``，也就是：

.. code-block:: c

    // 编译器看到 @property 时
    // 1. 先定义函数 x
    // 2. 调用 property(x)
    // 3. 将结果赋回名字 x

    // property(x) 在 C 层的等价代码
    PyObject *prop = PyProperty_Type.tp_new(&PyProperty_Type, args, NULL);
    ((PyPropertyObject *)prop)->prop_get = x_func;

``@x.setter`` 和 ``@x.deleter`` 也是类似的：

.. code-block:: c

    // property 的 setter 方法
    static PyObject *
    property_setter(PyObject *self, PyObject *func) {
        PyPropertyObject *prop = (PyPropertyObject *)self;
        // 创建新 property，复制旧字段 + 设置新的 prop_set
        PyPropertyObject *new_prop = copy_property(prop);
        new_prop->prop_set = func;
        return (PyObject *)new_prop;
    }

这就是 ``@x.setter`` 返回一个新 ``property`` 对象的原因——property 是不可变的。

通过示例脚本验证
----------------

运行 :file:`examples/property_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - property 的本质？
     - PyPropertyObject：包含 fget/fset/fdel 三个函数指针的描述符
   * - obj.x 访问路径？
     - 描述符查找 → property_descr_get → 调用 fget
   * - @x.setter 为什么返回新对象？
     - property 不可变，setter 创建副本并设置 prop_set
   * - 和普通方法的区别？
     - property 走 tp_descr_get，不走 tp_call

参考资料
--------

- :file:`Objects/descrobject.c` — PyProperty_Type 实现
