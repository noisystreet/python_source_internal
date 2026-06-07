sys.modules 与模块缓存
=============================

``sys.modules`` 是已导入模块的缓存。它保证每个模块只被加载一次。

第一问：模块缓存的作用
---------------

.. code-block:: python

    import sys
    sys.modules['math']  # 模块对象

当 ``import math`` 执行时：

#. 检查 ``sys.modules`` 中是否有 ``'math'``
#. 有 → 直接返回
#. 无 → 查找、加载、执行、放入 ``sys.modules``

第二问：缓存的清理
---------------

.. code-block:: python

    del sys.modules['math']  # 强制重新加载
    import math              # 这次会重新执行 math 模块代码

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
     - 缓存已导入模块，保证每个模块只加载一次
   * - 怎么强制重新加载？
     - ``del sys.modules['modname']`` 再 import
