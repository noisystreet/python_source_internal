配置与初始化 (initconfig)
====================================

``PyConfig`` 是 CPython 3.8+ 引入的配置结构，用于统一解释器的初始化参数。
它取代了旧版中零散的 ``Py_SetProgramName``、``Py_SetPath`` 等 API。

从一道题开始
------------

.. code-block:: python

    # 当你运行 python -X dev script.py 时
    # CPython 内部经历了什么？

    import sys
    print(sys.flags)

第一问：PyConfig 结构
---------------------

``PyConfig`` 是一个大结构体，包含所有可配置的解释器参数：

.. code-block:: c

    typedef struct PyConfig {
        int isolated;                  // 隔离模式（-I 标志）
        int use_environment;           // 是否读取环境变量
        int dev_mode;                  // 开发模式（-X dev）
        int utf8_mode;                 // UTF-8 模式
        int faulthandler;              // 注册 faulthandler
        int site_import;               // 是否 import site

        const wchar_t *program_name;   // 程序名 (sys.executable)
        const wchar_t *pythonpath_env; // PYTHONPATH 环境变量
        PyWideStringList argv;         // 命令行参数
        PyWideStringList warnings;     // 警告控制
        // ... 共约 50 个字段
    } PyConfig;

第二问：配置流程 — 分步详解
----------------------------

配置初始化按固定顺序执行：

.. mermaid::

    flowchart TD
        A["PyConfig_InitPythonConfig(&config)"] --> B["设置默认值"]
        B --> C["用户重写字段"]
        C --> D["PyConfig_SetBytesArgv(&config, argc, argv)"]
        D --> E["PyConfig_Read(&config)<br/>读取环境变量"]
        E --> F["Py_InitializeFromConfig(&config)"]
        F --> G["config 被消费<br/>不再使用"]

代码示例：

.. code-block:: c

    // Python/initconfig.c 中的典型用法
    PyStatus init_python(const char *program, int argc, char *argv[])
    {
        PyConfig config;

        // 1. 初始化默认配置
        PyConfig_InitPythonConfig(&config);
        // 等价于填充 config.isolated = 0, config.dev_mode = 0 等

        // 2. 设置程序名（影响 sys.executable、sys.path 的推导）
        PyConfig_SetBytesString(&config, &config.program_name, program);

        // 3. 设置参数
        PyConfig_SetBytesArgv(&config, argc, argv);

        // 4. 读取环境变量（PYTHONPATH, PYTHONDEVMODE 等）
        PyConfig_Read(&config);

        // 5. 初始化
        PyStatus status = Py_InitializeFromConfig(&config);

        // 6. 释放配置（初始化完成后不再需要）
        PyConfig_Clear(&config);

        return status;
    }

第三问：专用配置结构
--------------------

Python 3.8 还引入了 ``PyPreConfig``，在 ``PyConfig`` 之前生效：

.. code-block:: c

    // 预配置：在 Python 核心初始化之前
    PyPreConfig preconfig;
    PyPreConfig_InitPythonConfig(&preconfig);
    preconfig.utf8_mode = 1;  // 强制 UTF-8 模式

    Py_PreInitialize(&preconfig);

预配置只影响少量全局设置：编码、隔离模式、是否允许 ``site`` 导入。

通过示例脚本验证
----------------

运行：

.. code-block:: bash

    python -c "import sys; print(sys.flags)"
    python -X dev -c "import sys; print(sys.flags)"

观察 ``dev_mode``、``isolated`` 等标志的变化。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - PyConfig 是什么？
     - 统一的解释器配置结构（Python 3.8+）
   * - 怎么用？
     - ``PyConfig_InitPythonConfig`` → 设字段 → ``PyConfig_Read`` → ``Py_InitializeFromConfig``
   * - PyPreConfig 和 PyConfig 的区别？
     - PyPreConfig 在核心初始化前生效，只控制编码和隔离
   * - 配置释放？
     - ``PyConfig_Clear`` 在初始化完成后调用

参考资料
--------

- :file:`Python/initconfig.c` — PyConfig 实现
