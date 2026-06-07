解释器生命周期 — Python 的启动与关闭
============================================

CPython 解释器的生命周期分为预初始化、初始化、执行、终结四个阶段。

第一问：启动流程
-----------

.. code-block:: text

    Py_Main()
    → Py_InitializeFromConfig()
      → _PyRuntimeState_Init()
      → _PyInterpreterState_New()
      → _PyThreadState_New()
      → _Py_ReadyBuiltins()
      → _Py_ReadyTypes()
      → sys.modules 初始化
      → site.main() 执行
    → Py_BytesMain() / 执行脚本

第二问：关闭流程
-----------

.. code-block:: text

    Py_Finalize()
    → 调用退出函数
    → GC 清理
    → 关闭模块
    → 释放解释器状态
    → _PyRuntimeState_Fini()


小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 启动流程？
     - Py_InitializeFromConfig → 解释器/线程状态 → 内置模块 → site
   * - 关闭流程？
     - 退出函数 → GC → 关闭模块 → 释放状态

通过示例脚本验证
----------------

解释器生命周期在进程层面体现，可通过 ``sys.prefix``、``sys.executable``
等属性观察初始化后的环境。

