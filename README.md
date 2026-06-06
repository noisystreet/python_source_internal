# python-source-internal

> CPython 源码深度解读 —— 以文档为主、示例为辅，系统梳理 CPython 内部实现细节。

## 项目定位

面向有 Python 使用经验、希望深入理解 CPython 解释器实现的开发者。通过结构化文档 + 可运行的示例脚本，逐层拆解 CPython 的核心机制。

## 文档索引

| 文档 | 说明 |
|------|------|
| [架构总览](docs/ARCHITECTURE.rst) | CPython 分层架构与模块组织 |
| [分析文档目录](docs/) | 按子系统组织的源码解读 |
| [Sphinx 文档](docs/_build/index.html) | 本地构建的 HTML 文档（``make docs`` 后生成） |
| [示例脚本](examples/) | 可运行的配套示例 |
| [贡献指南](CONTRIBUTING.md) | 如何参与贡献 |
| [Agent 指引](AGENTS.md) | AI 协作规范 |

## 快速开始

```bash
# 安装依赖（仅示例脚本需要）
pip install -e ".[dev]"

# （可选）拉取 CPython 源码，方便对照阅读
git clone -b v3.14.5 https://github.com/python/cpython.git
export CPYTHON_SRC=$PWD/cpython

# 运行示例
python examples/hello_pyobject.py

# 运行测试
make test

# 构建文档
make docs
```

## 许可证

[MIT](LICENSE)
