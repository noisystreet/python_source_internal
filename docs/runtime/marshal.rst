编组与序列化 (marshal)
==============================

``marshal`` 模块是 CPython 内部的序列化格式，用于 ``.pyc`` 文件。

第一问：格式特点
-----------

- 只支持 Python 原生类型（int、str、tuple、list、dict、code 等）
- 速度快但不安全（反序列化不可信数据有风险）
- 用于 ``.pyc`` 文件和 ``__pycache__``

第二问：PyCodeObject 的序列化
---------------------------

代码对象通过 ``marshal`` 写入 ``.pyc`` 文件。


小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - marshal 用于什么？
     - .pyc 文件序列化，内部通信
   * - 安全吗？
     - 不安全，不可用于不可信数据

通过示例脚本验证
----------------

运行 :file:`examples/marshal_demo.py`。

