.. _runtime-marshal:

编组与序列化 (marshal)
==============================

.. epigraph::

   "Data is a precious thing and will last longer than the systems themselves."

   -- Tim Berners-Lee (on serialization)


``marshal`` 模块是 CPython 内部的序列化格式。它比 ``pickle`` 快，
但只支持 Python 原生类型，因此主要用于 ``.pyc`` 文件的存储。

从一道题开始
------------

.. code-block:: python

    import marshal
    data = marshal.dumps([1, 2, 3, "hello"])
    # b'\xdb\x03\x00\x00\x00e\x01\x00\x00\x00e\x02...
    marshal.loads(data)  # [1, 2, 3, 'hello']

marshal 的输出是二进制流，类型通过**类型码**标记。

第一问：类型码格式
------------------

marshal 对每种类型使用一个字节的类型码：

.. list-table::
   :header-rows: 1

   * - 类型码
     - 类型
   * - ``TYPE_INT`` (``'i'``)
     - 整数（4 字节）
   * - ``TYPE_LONG`` (``'l'``)
     - 长整数（任意精度）
   * - ``TYPE_FLOAT`` (``'f'``)
     - 浮点数（8 字节）
   * - ``TYPE_STRING`` (``'s'``)
     - 短字符串
   * - ``TYPE_TUPLE`` (``')'``)
     - 元组
   * - ``TYPE_LIST`` (``'['``)
     - 列表
   * - ``TYPE_DICT`` (``'{'``)
     - 字典
   * - ``TYPE_CODE`` (``'c'``)
     - 代码对象（PyCodeObject）
   * - ``TYPE_CODE2`` (``'C'``)
     - 代码对象 2（较新版本）
   * - ``TYPE_REF`` / ``TYPE_FLAG_REF``
     - 共享引用 / 引用标志

序列化格式：

.. code-block:: text

    marshal.dumps([1, 2]) 的内部二进制结构：

    TYPE_LIST    ([)
    n_elements  (\x02)
      TYPE_INT  (i) value(1)
      TYPE_INT  (i) value(2)

第二问：代码对象的序列化
------------------------

``.pyc`` 文件的核心就是序列化后的 ``PyCodeObject`` ：

.. mermaid::

    flowchart LR
        py["source.py"] --> compile["compile()"]
        compile --> code["PyCodeObject"]
        code --> marshal["marshal.dumps()"]
        marshal --> pyc["__pycache__/source.cpython-314.pyc"]
        pyc --> 反序列化["marshal.loads()"]
        反序列化 --> code2["PyCodeObject（重建）"]
        code2 --> ceval["ceval 执行"]

代码对象序列化的内容：

.. code-block:: c

    // marshal 对 PyCodeObject 的序列化（简化）
    void w_complex_object(PyObject *v)
    {
        if (PyCode_Check(v)) {
            // 写入 TYPE_CODE2 类型码
            W_TYPE(TYPE_CODE2, p);
            // 依次写入代码对象的各个字段
            w_byte(v->co_argcount, p);
            w_byte(v->co_nlocals, p);
            w_byte(v->co_stacksize, p);
            w_byte(v->co_flags, p);
            w_object(v->co_code, p);       // 字节码
            w_object(v->co_consts, p);     // 常量元组
            w_object(v->co_names, p);      // 名字元组
            w_object(v->co_varnames, p);   // 局部变量名
            // ...
        }
    }

第三问：marshal 与 pickle 的对比
--------------------------------

.. list-table::
   :header-rows: 1

   * - 特性
     - marshal
     - pickle
   * - 支持类型
     - 仅 Python 原生类型 + code 对象
     - 几乎任意 Python 对象
   * - 速度
     - 快
     - 中等（取决于协议版本）
   * - 跨版本兼容
     - 弱（格式可能变化）
     - 强（协议 5 兼容）
   * - 安全性
     - 不安全
     - 不安全
   * - 主要用途
     - .pyc 文件
     - 通用序列化

通过示例脚本验证
----------------

运行 :file:`examples/marshal_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - marshal 主要用于什么？
     - .pyc 文件序列化
   * - 支持什么类型？
     - int、str、list、tuple、dict、code 等原生类型
   * - 类型怎么标记？
     - 一个字节的类型码（TYPE_INT = 'i', TYPE_LIST = '[' 等）
   * - marshal 和 pickle 的区别？
     - marshal 更快但类型更少，主要用于内部
   * - 安全吗？
     - 不安全，不可用于不可信数据

参考资料
--------

- :ref:`compiler-import` — import 系统中 marshal 的使用
- :ref:`ceval-bytecodes` — 字节码序列化与反序列化
- :file:`Python/marshal.c` — marshal 实现
