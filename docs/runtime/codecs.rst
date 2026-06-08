Codec 系统 — 编码与解码基础设施
========================================

``codecs`` 模块提供了编码/解码的基础设施，允许 Python 在处理文本和字节
时支持数百种字符编码。

从一道题开始
------------

.. code-block:: python

    "你好".encode("utf-8")           # → b'\xe4\xbd\xa0\xe5\xa5\xbd'
    b'\xe4\xbd\xa0\xe5\xa5\xbd'.decode("utf-8")  # → '你好'

一个 ``.encode()`` 调用的背后，CPython 需要查找注册表、找到编解码器、执行转换。

第一问：编码查找链
------------------

.. mermaid::

    flowchart LR
        py["str.encode('utf-8')"] --> registry["codecs.lookup('utf-8')"]
        registry --> search["搜索注册表<br/>按名称查找"]
        search --> found{"找到?"}
        found -->|"是"| codec["返回 CodecInfo"]
        found -->|"否"| normalize["名称标准化<br/>（别名、大小写）"]
        normalize --> search2["再次搜索"]
        search2 --> not_found{"仍未找到?"}
        not_found -->|"是"| error["LookupError"]
        not_found -->|"否"| codec
        codec --> encode_func["调用 CodecInfo.encode<br/>（str → bytes）"]
        encode_func --> result["返回 bytes"]

``codecs.lookup`` 是核心查找函数：

.. code-block:: python

    # Lib/encodings/__init__.py 中的查找逻辑（简化）
    def search_function(encoding):
        # 1. 规范化编码名
        normalized = encoding.replace('-', '_').lower()

        # 2. 尝试导入 Lib/encodings/<normalized>.py
        try:
            mod = __import__(f'encodings.{normalized}')
            return mod.getregentry()
        except ImportError:
            pass

        # 3. 尝试用户注册的自定义编解码器
        for func in codecs._custom_codecs:
            result = func(encoding)
            if result is not None:
                return result

        # 4. 未找到
        return None

第二问：CodecInfo 对象
-----------------------

每个注册的编解码器返回一个 ``CodecInfo`` 对象：

.. code-block:: python

    >>> import codecs
    >>> info = codecs.lookup("utf-8")
    >>> info.name
    'utf-8'
    >>> info.encode("hello")
    (b'hello', 5)          # (编码结果, 消耗的字符数)
    >>> info.decode(b"hello")
    ('hello', 5)           # (解码结果, 消耗的字节数)

``CodecInfo`` 包含编码/解码函数和流式处理接口。

第三问：自定义编解码器
----------------------

通过 ``codecs.register`` 可以注册自定义编码：

.. code-block:: python

    import codecs

    class MyCodec(codecs.Codec):
        def encode(self, s, errors='strict'):
            return s.encode('utf-16-be'), len(s)

        def decode(self, s, errors='strict'):
            return s.decode('utf-16-be'), len(s)

    def search(encoding):
        if encoding == 'mycodec':
            return codecs.CodecInfo(
                name='mycodec',
                encode=MyCodec().encode,
                decode=MyCodec().decode,
            )
        return None

    codecs.register(search)

    print("你好".encode("mycodec"))  # 使用自定义编码器

通过示例脚本验证
----------------

运行 :file:`examples/codecs_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 编码器怎么查找？
     - ``codecs.lookup(name)`` → 搜索注册表 → 返回 CodecInfo
   * - CodecInfo 包含什么？
     - name + encode 函数 + decode 函数
   * - 编码器存在哪？
     - ``Lib/encodings/`` 目录（按文件名导入）
   * - 可以自定义编码吗？
     - 可以，通过 ``codecs.register`` 注册搜索函数
   * - encode/decode 的返回值？
     - ``(result, consumed_count)`` 元组

参考资料
--------

- :file:`Python/codecs.c` — codec 注册表
