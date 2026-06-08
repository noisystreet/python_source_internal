导入机制 — import 语句的实现
===================================

.. epigraph::

   "Nothing comes from nothing."

   -- Lucretius, De Rerum Natura (on modules and creation)


Python 的 ``import`` 语句触发了一整套查找、加载、缓存机制。
这一节来看 CPython 如何实现模块导入。

从一道题开始
------------

.. code-block:: python

    import math

    # CPython 内部发生了什么？
    # 1. 查找 'math'（sys.modules 缓存）
    # 2. 没找到 → 查找（finder）
    # 3. 找到 → 加载（loader）
    # 4. 执行模块代码
    # 5. 放入 sys.modules
    # 6. 绑定到当前作用域

第一问：导入入口
----------------

``import`` 语句的字节码是 ``IMPORT_NAME`` ：

.. code-block:: text

    0 LOAD_CONST  0 (0)         # level
    2 LOAD_CONST  1 (None)      # fromlist
    4 IMPORT_NAME 0 (math)      # → 调用 __import__
    6 STORE_NAME  0 (math)

``IMPORT_NAME`` 调用内置函数 ``__import__``，它在 C 层对应
``PyImport_ImportModuleLevelObject`` 。

第二问：查找和加载
------------------

CPython 的导入系统分为两步：

**查找 (Find)**
  ``sys.meta_path`` 中的 finder 依次尝试。

  - ``_frozen_importlib.BuiltinImporter`` ：内置模块（如 ``sys`` ）
  - ``_frozen_importlib.FrozenImporter`` ：冻结模块
  - ``_frozen_importlib.PathFinder`` ：基于 ``sys.path`` 的文件查找

**加载 (Load)**
  Finder 返回一个 spec（模块规格），传给 Loader 执行。

  - 源码模块：读取 ``.py`` 文件，编译，执行
  - 扩展模块：加载 ``.so`` / ``.pyd`` 动态库

第三问：模块缓存
----------------

``sys.modules`` 是导入结果的缓存：

.. code-block:: python

    import sys
    sys.modules['math']  # 已导入的模块

``IMPORT_NAME`` 的第一步就是检查 ``sys.modules`` 。如果存在，直接返回。
否则继续查找和加载。

通过示例脚本验证
----------------

运行 :file:`examples/import_demo.py`：

.. code-block:: text

    --- sys.modules 缓存 ---
    sys  已导入
    math 已导入
    os   已导入

    --- 导入前后对比 ---
    导入前 'json' in sys.modules: False
    导入后 'json' in sys.modules: True

    --- 查找路径 ---
    sys.path 包含: current_dir, site-packages, ...

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - import 的入口？
     - IMPORT_NAME 字节码 → __import__ 函数
   * - 查找顺序？
     - sys.meta_path 中的 finder 按序尝试
   * - 模块缓存在哪？
     - sys.modules 字典
   * - 两种模块类型？
     - 源码模块 (.py) 和扩展模块 (.so/.pyd)

参考资料
--------

- :file:`Python/import.c` — 导入实现
- :pep:`451` — ModuleSpec
