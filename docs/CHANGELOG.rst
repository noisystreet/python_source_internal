Changelog
=========

v0.2.0 (2026-06-07)
-------------------

新增
^^^^

* 全书自动编号 — 根 toctree 启用 ``:numbered:`` （1. ARCHITECTURE 到 3.15 super）
* Read the Docs 在线构建配置（:file:`.readthedocs.yaml`）+ 徽章
* 为 15 个核心章节添加参考资料（PEP 编号、源码路径、外部链接）
* CPython 源码仓库导览（:doc:`/guide/cpython-repo`）— 目录结构 / 构建 / 调试 / gdb

扩充
^^^^

* 扩写 11 个薄弱章节（+1000 行, +8 Mermaid 图）
  - concurrency/critical-section: PyMutex + 锁类型 + 使用场景表
  - extensions/c-api-overview / limited-api / ctypes-ffi: 完整扩写
  - runtime/lifecycle / marshal / codecs: Mermaid 流程图 + C 代码
  - modules/sys-modules: import 查找链 Mermaid
  - exceptions/: 异常传播 + traceback 链表 + settrace 事件分发

修复
^^^^

* RST 内联标记与 CJK 全角标点相邻导致 Docutils 解析失败（53→0 警告）
* RST 标题下划线不足（CJK 双字宽导致 45 个 underline warning）
* 侧边栏分类标题重复（移除 toctree ``:caption:``）
* 侧边栏子系统展开重复（子 toctree 改为 ``:hidden:``）

变更
^^^^

* 删除空的 ``src/`` 包及 ``pyproject.toml`` 中相关配置
* 删除 ``tests/`` 下空占位文件（``__init__.py``、``fixtures/``、``unit/``）
* ``docs/index.rst`` 子系统 toctree 统一为 ``:maxdepth: 1``
* 示例脚本不再需要 ``__init__.py`` 包化

CI
^^

* GitHub Actions — lint / test / docs 三作业并行
* Read the Docs — ubuntu 24.04 + Python 3.13

v0.1.0 (2026-06-05)
-------------------

首次发布。项目骨架搭建完成，涵盖 CPython 3.14 九个核心子系统。

新增
^^^^

* 文档：52 篇内容章节覆盖 9 个子系统

  - 对象模型（15 篇）：PyObject、PyTypeObject、引用计数、函数与代码对象、
    迭代器与生成器、int/str/dict/list/tuple/set/weakref、描述符、
    ``__slots__``、``super``
  - 字节码执行引擎（6 篇）：解释循环、字节码指令、调用约定、特化、Tier 2、JIT
  - 编译系统（6 篇）：Tokenizer、PEG Parser、AST、符号表、字节码生成、导入机制
  - 内存管理（4 篇）：obmalloc、分代 GC、环形引用检测、Arena
  - 并发与并行（4 篇）：GIL、自由线程、临界区、async/await
  - 异常与调试（4 篇）：异常处理链、Traceback、settrace、远程调试
  - 模块系统（3 篇）：模块对象、内置模块、sys.modules
  - 扩展与 C API（7 篇）：API 分层、Limited API、动态加载、模块初始化、
    多阶段初始化、内存 API、ctypes
  - 运行时系统（6 篇）：生命周期、解释器状态、线程状态、PyConfig、marshal、codecs
* 架构总览（:doc:`ARCHITECTURE`）：分层架构 Mermaid 图 + 核心数据结构交叉引用
* 风格统一：全书 55 内容章节全部具备"从一道题开始 → 通过示例脚本验证 → 小结 QA 表格"
* 示例脚本：39 个配套可运行脚本，冒烟测试全部通过
* 构建配置：``chore: 删除空的 src/ 包，清理相关配置``
* 贡献指南 / 安全政策 / Changelog

已知问题
--------

* ``__all__`` 未在 ``docs/conf.py`` 中配置
* Windows 平台下的构建未经测试
