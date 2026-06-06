# AGENTS.md — AI 协作规范

本文档是给编程 Agent 的必读缩略版，涵盖本项目的行为约束与验证命令。

## 项目身份

- **项目**：python-source-internal — CPython 源码深度解读
- **技术栈**：Python ≥ 3.11，pytest + ruff + mypy
- **目录结构**：

```
├── docs/               # 解读文档（RST，核心产出）
├── examples/           # 可运行的示例脚本
├── src/                # Python 工具包
├── tests/              # 测试（unit / integration / fixtures）
├── scripts/            # 辅助脚本
├── .github/            # CI、Issue/PR 模板
├── AGENTS.md           # 本文件
├── Makefile            # 统一命令入口
├── pyproject.toml      # 项目配置
├── README.md           # 项目简介
├── CONTRIBUTING.md     # 贡献指南
├── SECURITY.md         # 安全政策
├── CHANGELOG.md        # 变更日志
├── LICENSE             # MIT 许可证
├── .editorconfig       # 编辑器配置
├── .pre-commit-config.yaml
└── .env.example        # 环境变量示例
```

## 硬约束

### 依赖方向
- `docs/` 和 `examples/` 可以引用 `src/`，反之不得引用示例中的代码
- `src/python_source_internal/core/` 可引用 `models/`，禁止反向依赖

### 禁止引入的库
- 不允许添加纯文档项目不需要的运行时依赖（文档解读本身不应引入 web 框架、ORM 等）
- 测试 / 开发工具仅允许添加至 `[project.optional-dependencies]` 的 `dev` / `lint` 组

### 文档修改权限
- Agent 可直接修改 `docs/` 目录下的新增文档章节
- 修改 `docs/ARCHITECTURE.rst` 的总体结构或路线图需经人工确认
- `AGENTS.md` 本身不允许 Agent 自行修改

### 安全红线
- 不得在代码或提交中包含密钥、Token、证书等敏感信息
- 示例脚本中不得使用 `eval()`、`exec()` 执行用户输入

### 测试要求
- 新增 `src/` 下的模块时必须同时编写单元测试
- 新增示例脚本鼓励但不必强制编写测试
- 最低覆盖率：`src/` 下代码 ≥ 80%

## 验证命令

Agent 完成修改后必须运行：

```bash
make lint    # ruff + mypy
make test    # pytest
```

## 工程与代码质量

- **静态分析**：`ruff` (E/F/W/I/N/UP) + `mypy --strict`
- **格式化**：`ruff format`，行宽 88
- 本项目以解读文档为主，`src/` 下的代码仅为辅助工具，保持轻量

## 文档与语言约定

- 解读文档（`docs/`）使用 RST 格式 + Sphinx 构建
- 使用中文撰写，关键术语首次出现标注英文原文
- 代码注释使用英文
- `examples/` 下脚本的 docstring 和注释使用英文
- **框图和流程图优先使用 Mermaid 格式**（``.. mermaid::`` 指令），仅在 Mermaid 无法表达时使用 ASCII art

## 协作入口

- 安全政策见 [SECURITY.md](SECURITY.md)
- 贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)
