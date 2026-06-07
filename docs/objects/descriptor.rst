属性访问与描述符
==================

当你在 Python 中写 ``obj.attr`` 时，CPython 内部走了一条精心设计的查找路径。
这一节我们来拆开它。

从一道题开始
------------

.. code-block:: python

    class A:
        x = 10          # 普通类属性
        @property
        def y(self):    # 描述符
            return 42

    a = A()
    print(a.x)  # 10 — 从类属性字典找到
    print(a.y)  # 42 — 属性访问被完全改变了！

为什么 ``a.x`` 和 ``a.y`` 的访问路径完全不同？因为 ``property`` 是一个**描述符** （descriptor）——它实现了 ``__get__`` 方法，从而劫持了属性查找过程。

.. mermaid::

    flowchart TD
        attr["a.y"] --> lookup["PyObject_GenericGetAttr(a, 'y')"]
        lookup --> search["在 a.__dict__ 中找 'y'"]
        search -->|"没找到"| type_lookup["在 type(a).__dict__ 中找 'y'"]
        type_lookup --> found{"找到了?"}
        found -->|"是, 且是数据描述符"| descr_get["调用 y.__get__(a, type(a))"]
        found -->|"是, 但不是描述符"| return_val["返回值本身"]
        descr_get --> result["42"]

第一问：描述符协议是什么？
--------------------------

描述符就是实现了 **三个特殊方法之一** 的对象：

.. list-table::
   :header-rows: 1

   * - 方法
     - C 层函数指针
     - 作用
   * - ``__get__(self, obj, type=None)``
     - ``tp_descr_get``
     - 获取属性值时调用
   * - ``__set__(self, obj, value)``
     - ``tp_descr_set``
     - 设置属性值时调用
   * - ``__delete__(self, obj)``
     - （通过 ``tp_descr_set`` 的第二个参数）
     - 删除属性时调用

在 C 层，这些函数的签名是：

.. code-block:: c

    // 描述符的 __get__：返回属性值
    typedef PyObject *(*descrgetfunc)(PyObject *descr,     // 描述符对象本身
                                       PyObject *obj,       // 被访问的实例
                                       PyObject *type);     // 实例的类型

    // 描述符的 __set__：设置属性值；value=NULL 时表示删除
    typedef int (*descrsetfunc)(PyObject *descr, PyObject *obj, PyObject *value);

这些函数指针就存储在 ``PyTypeObject`` 的 ``tp_descr_get`` 和 ``tp_descr_set``
字段中。

第二问：数据描述符 vs 非数据描述符
----------------------------------

描述符分为两种，它们的优先级不同：

**数据描述符 (Data Descriptor)**
  同时实现了 ``__get__`` 和 ``__set__`` / ``__delete__``

  - 例如：``property`` 、``member`` （C 结构体成员）
  - **优先级高于实例字典** ：即使 ``obj.__dict__`` 中有同名属性，数据描述符也会覆盖它

**非数据描述符 (Non-Data Descriptor)**
  只实现了 ``__get__``

  - 例如：普通方法（``function`` 类型）、``staticmethod`` 、``classmethod``
  - **优先级低于实例字典** ：如果 ``obj.__dict__`` 中有同名属性，优先使用实例字典中的值

.. mermaid::

    flowchart TD
        lookup["属性查找优先级"] --> data["1. 数据描述符 (data descriptor)"]
        lookup --> instance["2. 实例 __dict__"]
        lookup --> non_data["3. 非数据描述符 (non-data descriptor)"]
        lookup --> class_dict["4. 类 __dict__"]
        lookup --> parent["5. 父类 (按 MRO)"]

这个优先级顺序定义在 ``PyObject_GenericGetAttr`` 中，是 CPython 属性查找的核心逻辑。

第三问：属性查找的 C 层实现
---------------------------

CPython 的属性查找默认走 ``PyObject_GenericGetAttr`` ：

.. code-block:: c

    // Objects/object.c 中的通用属性查找（简化）
    PyObject *PyObject_GenericGetAttr(PyObject *obj, PyObject *name)
    {
        // 1. 获取类型对象和类型字典
        PyTypeObject *type = Py_TYPE(obj);
        PyObject *meta_dict = _PyType_GetBasesDict(type);
        descrgetfunc f = NULL;

        // 2. 在类型 MRO 中查找 name
        //    如果找到且是描述符，记录其 tp_descr_get 和 tp_descr_set
        PyObject *descr = _PyType_Lookup(type, name);
        if (descr != NULL) {
            f = Py_TYPE(descr)->tp_descr_get;
            if (f != NULL && Py_TYPE(descr)->tp_descr_set != NULL) {
                // 是数据描述符 → 直接调用 __get__，跳过实例字典
                return f(descr, obj, (PyObject *)type);
            }
        }

        // 3. 在实例字典 obj.__dict__ 中查找
        PyObject *dict = _PyObject_GetDictPtr(obj);
        if (dict != NULL) {
            PyObject *value = PyDict_GetItem(dict, name);
            if (value != NULL) {
                Py_INCREF(value);
                return value;
            }
        }

        // 4. 如果是非数据描述符，调用 __get__
        if (f != NULL) {
            return f(descr, obj, (PyObject *)type);
        }

        // 5. 如果找到了普通属性（不是描述符），直接返回
        if (descr != NULL) {
            Py_INCREF(descr);
            return descr;
        }

        // 6. 都没找到 → 尝试 __getattr__
        return _PyObject_GenericGetAttrWithDict(obj, name, dict, 1);
    }

这个函数清晰地展示了属性查找的**五步优先级** 。

第四问：方法调用也是描述符
--------------------------

当你写 ``obj.method()`` 时，你实际上触发了描述符协议：

.. code-block:: python

    class MyClass:
        def method(self):
            return 42

    obj = MyClass()
    print(obj.method)   # <bound method ...>
    print(MyClass.method)  # <function ... at 0x...>

``obj.method`` 和 ``MyClass.method`` 返回不同的东西——因为 ``function`` 类型实现了 ``__get__`` （非数据描述符）。

在 C 层，``PyFunctionObject`` 的 ``tp_descr_get`` 指向 ``func_descr_get`` ：

.. code-block:: c

    static PyObject *
    func_descr_get(PyObject *func, PyObject *obj, PyObject *type)
    {
        if (obj == Py_None || obj == NULL) {
            // 通过类访问 → 返回函数本身
            Py_INCREF(func);
            return func;
        }
        // 通过实例访问 → 创建方法对象 (bound method)
        return PyMethod_New(func, obj);
    }

``PyMethod_New`` 创建一个 ``PyMethodObject`` （方法对象），它包装了函数和实例。
当你调用 ``bound_method()`` 时，实例自动作为第一个参数传入。

.. code-block:: c

    // methodobject.c 中方法调用的实现
    static PyObject *
    method_vectorcall(PyObject *method, PyObject *const *args,
                      size_t nargsf, PyObject *kwnames)
    {
        PyMethodObject *m = (PyMethodObject *)method;
        // 把实例插到参数列表最前面
        return _PyObject_VectorcallTstate(tstate, m->m_func,
                                          &m->m_self, 1 + nargsf, kwnames,
                                          method);
    }

.. mermaid::

    flowchart LR
        obj_method["obj.method"] --> func["MyClass.method (function 对象)"]
        func -->|"tp_descr_get 被调用"| bound["PyMethodObject<br/>m_func = method<br/>m_self = obj"]
        bound --> call["obj.method() → method(self=obj, ...)"]

第五问：property 的 C 实现
--------------------------

``property`` 是最常用的自定义描述符。在 C 层，它是一个 ``propertyobject`` ：

.. code-block:: c

    typedef struct {
        PyObject_HEAD
        PyObject *prop_get;     // getter 函数
        PyObject *prop_set;     // setter 函数
        PyObject *prop_del;     // deleter 函数
        PyObject *prop_doc;     // 文档字符串
        int getter_doc;         // 是否使用 getter 的文档
    } propertyobject;

它的 ``tp_descr_get`` 实现很简单：

.. code-block:: c

    static PyObject *
    property_descr_get(PyObject *self, PyObject *obj, PyObject *type)
    {
        propertyobject *prop = (propertyobject *)self;
        if (obj == NULL || obj == Py_None) {
            // 通过类访问 → 返回 property 对象本身
            Py_INCREF(prop);
            return (PyObject *)prop;
        }
        if (prop->prop_get == NULL) {
            PyErr_SetString(PyExc_AttributeError, "unreadable attribute");
            return NULL;
        }
        // 调用 getter
        return PyObject_CallOneArg(prop->prop_get, obj);
    }

当你写 ``@property`` 时，Python 在字节码层面创建 ``property(fget)`` 对象，
然后把它赋值给类属性。从此所有属性访问都经过 ``property_descr_get`` 。

第六问：staticmethod 和 classmethod 也是描述符
----------------------------------------------

``staticmethod`` 和 ``classmethod`` 也是通过描述符协议实现的：

.. code-block:: python

    class MyClass:
        @staticmethod
        def f(): pass          # 不接收 self

        @classmethod
        def g(cls): pass       # 接收 cls 而非 self

**staticmethod** ：``tp_descr_get`` 直接返回被包装的函数，不创建 bound method。
这样 ``obj.f()`` 和 ``MyClass.f()`` 行为一致——都直接调用函数。

**classmethod** ：``tp_descr_get`` 创建一个 bound method，但第一个参数绑定的是类（``type(obj)`` ），
而不是实例（``obj`` ）。

在 C 层，这对应两个不同的类型：``PyStaticMethod_Type`` 和 ``PyClassMethod_Type`` 。

.. code-block:: c

    // staticmethod 的 __get__
    static PyObject *
    sm_descr_get(PyObject *self, PyObject *obj, PyObject *type)
    {
        // 直接返回被包装的函数
        return Py_NewRef(staticmethod_func(self));
    }

    // classmethod 的 __get__
    static PyObject *
    cm_descr_get(PyObject *self, PyObject *obj, PyObject *type)
    {
        // 创建绑定到类的 bound method
        return PyMethod_New(classmethod_func(self),
                            Py_XNewRef(type));
    }

第七问：slot 描述符（PyMemberDef / PyGetSetDef）
------------------------------------------------

CPython 内部还有两种 C 级别的描述符，用于暴露 C 结构体成员：

**PyMemberDescrObject** （基于 ``PyMemberDef`` ）：
  对应 C 结构体的成员变量。例如 ``object.__dict__`` 、``func.__name__`` 。

.. code-block:: c

    typedef struct {
        PyDescr_COMMON;
        PyMemberDef *d_member;  // 描述了偏移量、类型、标志
    } PyMemberDescrObject;

    // 使用示例：PyMemberDef 描述结构体字段的位置
    static PyMemberDef function_members[] = {
        {"__name__", _Py_T_OBJECT, offsetof(PyFunctionObject, func_name),
         Py_READONLY, "function name"},
        {NULL}
    };

**PyGetSetDescrObject** （基于 ``PyGetSetDef`` ）：
  对应 C 结构体的"属性"——有 getter 和 setter 函数。

.. code-block:: c

    typedef struct {
        PyDescr_COMMON;
        PyGetSetDef *d_getset;  // getter/setter 函数指针
    } PyGetSetDescrObject;

    // 使用示例
    static PyGetSetDef object_getset[] = {
        {"__dict__", &object_get_dict, &object_set_dict, ...},
        {NULL}
    };

这两种描述符都是**数据描述符** （同时实现了 get 和 set），所以优先级高于实例字典。

通过示例脚本验证
----------------

运行 :file:`examples/descriptor_demo.py`：

.. code-block:: text

    --- 描述符优先级 ---
    数据描述符 > 实例 __dict__ > 非数据描述符

    --- property 描述符 ---
    obj.y → 调用 getter，返回 42

    --- 方法描述符 ---
    obj.method → 自动绑定到 obj
    MyClass.method → 返回函数本身

    --- 自定义描述符 ---
    使用 __get__ 实现验证逻辑

    --- staticmethod vs classmethod ---
    staticmethod: 不绑定
    classmethod: 绑定到类

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 描述符是什么？
     - 实现了 ``__get__`` / ``__set__`` 的对象
   * - 数据描述符 vs 非数据描述符
     - 数据描述符有 set（优先级最高）；非数据描述符只有 get
   * - 属性查找顺序？
     - 数据描述符 → 实例 __dict__ → 非数据描述符 → 类 → MRO
   * - 方法调用怎么工作？
     - function.__get__ 创建 bound method
   * - property 怎么实现？
     - propertyobject 的 tp_descr_get 调用 getter 函数
   * - 描述符有哪些 C 级别实现？
     - PyMemberDescrObject（结构体成员）+ PyGetSetDescrObject（getter/setter）
