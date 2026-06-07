配置与初始化 (initconfig)
====================================

``PyConfig`` 是 CPython 3.8+ 引入的配置结构，用于统一解释器的初始化参数。

第一问：PyConfig 结构
------------------

.. code-block:: c

    typedef struct PyConfig {
        int isolated;             // 隔离模式
        int use_environment;      // 是否读环境变量
        const wchar_t *program_name;  // 程序名
        const wchar_t *pythonpath_env; // PYTHONPATH
        PyWideStringList argv;    // 命令行参数
        PyWideStringList warnings; // 警告控制
        // ...
    } PyConfig;

第二问：配置流程
-----------

.. code-block:: c

    PyConfig config;
    PyConfig_InitPythonConfig(&config);
    config.isolated = 1;
    Py_InitializeFromConfig(&config);
