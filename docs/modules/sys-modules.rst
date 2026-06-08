sys.modules 与模块缓存
=============================

.. epigraph::

   "Memory is the treasury and guardian of all things."

   -- Cicero (on module caching)


``sys.modules`` 是已导入模块的缓存字典。它保证每个模块只被加载一次，
并提供了一个受限的命名空间隔离。

从一道题开始
------------

.. code-block:: python

    import sys
    import math

    # sys.modules 存了所有已导入的模块
    sys.modules['math'] is math  # True

    # 如果从 sys.modules 中删除，再 import 会重新执行模块代码
    del sys.modules['math']
    import math  # 这次会重新编译执行 math.py

第一问：模块缓存的作用
----------------------

当 ``import math`` 执行时，CPython 的查找流程：

.. mermaid::

    flowchart TD
        import["import math"] --> check{"sys.modules 中<br/>有 'math'?"}
        check -->|"有"| direct["直接返回缓存"]
        check -->|"无"| finder["meta_path finder 依次尝试"]
        finder --> builtin["BuiltinImporter<br/>检查内置模块表"]
        builtin --> frozen["FrozenImporter<br/>检查冻结模块"]
        frozen --> path["PathFinder<br/>在 sys.path 中查找"]
        path --> found{"找到 .py/.so?"}
        found -->|"是"| load["Loader 加载 + 执行"]
        load --> cache["存入 sys.modules"]
        cache --> return["返回模块对象"]
        found -->|"否"| error["ModuleNotFoundError"]

第二问：sys.modules 的键值结构
-------------------------------

``sys.modules`` 是一个普通的 ``dict`` ：

.. code-block:: python

    >>> import sys
    >>> type(sys.modules)
    <class 'dict'>
    >>> len(sys.modules)  # 启动后大约 30-50 个模块
    48
    >>> sys.modules['math']
    <module 'math' from '/usr/lib/python3.14/math.py'>

键是模块名（``str`` ），值是模块对象（``PyModuleObject`` ）。
对于子模块如 ``os.path``，键是 ``'os.path'``，值是 ``os.path`` 模块对象本身。

第三问：缓存的清理与重载
------------------------

以下操作可以操作 ``sys.modules`` 缓存：

.. code-block:: python

    # 查看
    import math
    'math' in sys.modules  # True

    # 删除（强制重新加载）
    del sys.modules['math']
    import math  # 重新执行 math 模块

    # 直接插入（注册伪造模块）
    sys.modules['fake'] = object()
    import fake  # 不会报错

.. warning::

   ``del sys.modules['modname']`` 不会释放已经被其他模块引用了的模块对象。
   如果 ``other.py`` 中已经执行了 ``import math``，那么 ``other.math`` 仍然
   指向旧的模块对象。新的 ``import math`` 会创建一个新的模块实例。

通过示例脚本验证
----------------

运行 :file:`examples/sysmodules_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - sys.modules 的作用？
     - 缓存所有已导入的模块
   * - 查找顺序？
     - sys.modules → BuiltinImporter → FrozenImporter → PathFinder
   * - 怎么强制重新加载？
     - ``del sys.modules['modname']`` 再 import
   * - 删除缓存会释放模块吗？
     - 不会，其他引用仍持有旧对象

参考资料
--------

- :file:`Python/import.c` — 模块缓存管理
