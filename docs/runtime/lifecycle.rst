解释器生命周期 — Python 的启动与关闭
============================================

CPython 解释器的生命周期分为预初始化、初始化、执行、终结四个阶段。

从一道题开始
------------

.. code-block:: bash

    $ python script.py

这个命令背后，CPython 经历了哪些步骤才能开始执行你的代码？

第一问：启动流程
----------------

完整的启动流程分为六个阶段：

.. mermaid::

    flowchart TD
        main["python.c<br/>main()"] --> phase1["阶段 1: 预初始化<br/>Py_PreInitialize"]
        phase1 --> phase2["阶段 2: 配置<br/>PyConfig_InitPythonConfig"]
        phase2 --> phase3["阶段 3: 初始化核心<br/>Py_InitializeFromConfig"]
        phase3 --> sub_init["子步骤："]
        sub_init --> s1["_PyRuntimeState_Init<br/>运行时全局状态"]
        sub_init --> s2["_PyInterpreterState_New<br/>创建解释器"]
        sub_init --> s3["_PyThreadState_New<br/>创建主线程"]
        sub_init --> s4["_Py_ReadyBuiltins<br/>初始化内置模块"]
        sub_init --> s5["_Py_ReadyTypes<br/>注册内置类型"]
        sub_init --> s6["sys.modules 初始化<br/>import site"]
        phase3 --> phase4["阶段 4: 执行脚本"]
        phase4 --> script["编译并执行 script.py"]
        script --> result["输出结果"]
        result --> phase5["阶段 5: 终结<br/>Py_Finalize"]
        phase5 --> cleanup["释放所有资源"]

.. code-block:: c

    // Python/pylifecycle.c 的简化流程
    int Py_BytesMain(int argc, char **argv)
    {
        // 1. 预初始化
        PyPreConfig preconfig;
        PyPreConfig_InitPythonConfig(&preconfig);
        Py_PreInitialize(&preconfig);

        // 2. 配置
        PyConfig config;
        PyConfig_InitPythonConfig(&config);
        PyConfig_SetBytesArgv(&config, argc, argv);

        // 3. 初始化
        Py_InitializeFromConfig(&config);

        // 4. 运行脚本
        Py_BytesRunMain();

        // 5. 终结
        Py_Finalize();
        return 0;
    }

第二问：Py_InitializeFromConfig 内部
------------------------------------

``Py_InitializeFromConfig`` 是初始化的核心函数，它按顺序执行：

.. code-block:: c

    // pylifecycle.c 中的初始化顺序（简化）
    PyStatus Py_InitializeFromConfig(const PyConfig *config)
    {
        // 1. 初始化运行时全局状态
        _PyRuntimeState_Init(&_PyRuntime);

        // 2. 创建主解释器
        PyInterpreterState *interp = _PyInterpreterState_New();

        // 3. 创建主线程状态
        PyThreadState *tstate = _PyThreadState_New(interp);

        // 4. 初始化 GIL（必须在线程状态就绪后）
        take_gil(tstate);

        // 5. 准备内置模块
        _Py_ReadyBuiltins(tstate);

        // 6. 准备内置类型（int, str, dict 等进入 tp_ready）
        _Py_ReadyTypes(tstate);

        // 7. 加载 sys 模块并配置 sys.path
        _PySys_Init(tstate);

        // 8. 执行 site.main()（处理 .pth 文件、site-packages）
        _PyImport_FixupCoreModules(tstate);
        _PyImport_InitExternal(tstate);
    }

第三问：关闭流程
----------------

终结阶段按初始化的逆序执行资源释放：

.. code-block:: c

    void Py_Finalize(void)
    {
        // 1. 调用 atexit 注册的函数
        _PyAtExit_Call(tstate);

        // 2. 调用模块的 m_free 函数
        _PyImport_Cleanup(tstate);

        // 3. 运行 GC 清理循环引用
        _PyGC_Collect(tstate);

        // 4. 销毁所有线程状态
        _PyThreadState_Clear(tstate);

        // 5. 销毁解释器状态
        _PyInterpreterState_Clear(interp);

        // 6. 释放运行时全局状态
        _PyRuntimeState_Fini(&_PyRuntime);
    }

通过示例脚本验证
----------------

解释器生命周期在进程层面体现，可通过以下方式观察：

.. code-block:: bash

    python -c "
    import sys
    print(f'sys.prefix: {sys.prefix}')
    print(f'sys.executable: {sys.executable}')
    print(f'sys.path: {sys.path[:3]}')
    print(f'sys.flags: {sys.flags}')
    "

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - 总共有几个阶段？
     - 预初始化 → 配置 → 初始化 → 执行 → 终结
   * - Py_InitializeFromConfig 做了什么？
     - 运行时 → 解释器 → 线程 → GIL → 内置模块 → 类型 → sys → site
   * - 关闭的顺序？
     - atexit → 模块清理 → GC → 线程 → 解释器 → 运行时
   * - 主入口函数在哪？
     - ``Programs/python.c`` → ``Py_BytesMain()``

参考资料
--------

- :file:`Python/pylifecycle.c` — 生命周期
