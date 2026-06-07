Codec 系统
================

``codecs`` 模块提供了编码/解码的基础设施。

第一问：编码查找链
---------------

.. code-block:: text

    "你好".encode("utf-8")
    → 查找 'utf-8' 编码器
    → 调用 utf-8 编码函数
    → 返回 bytes

第二问：Codec 注册
---------------

.. code-block:: python

    import codecs
    def my_codec(encoding):
        if encoding == "mycodec":
            return ...  # 返回 CodecInfo

    codecs.register(my_codec)
