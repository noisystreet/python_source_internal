# python-source-internal

> CPython 源码深度解读 —— 以文档为主、示例为辅，系统梳理 CPython 内部实现细节。

[![Documentation Status](https://readthedocs.org/projects/python-source-internal/badge/?version=latest)](https://python-source-internal.readthedocs.io/zh-cn/latest/?badge=latest)

## 文档

| 文档 | 说明 |
|------|------|
| [在线 HTML 文档](https://python-source-internal.readthedocs.io/zh-cn/latest/) | Read the Docs 自动构建 |
| [架构总览](docs/ARCHITECTURE.rst) | CPython 分层架构与子系统索引 |
| [源码仓库导览](docs/guide/cpython-repo.rst) | 仓库布局 / 构建 / 调试 |
| [示例脚本](examples/) | 41 个可运行配套脚本 |
| [贡献指南](CONTRIBUTING.md) | 如何参与 |

## 项目统计

| 指标 | 数值 |
|------|------|
| **文档章节** | 56 篇（9 子系统 + 1 开发指南） |
| **文档行数** | ~10,300 行 RST |
| **C 代码示例** | 189 个 ``code-block:: c`` |
| **Mermaid 图** | 40+ 张 |
| **示例脚本** | 41 个（~4,700 行 Python） |
| **测试** | 41/41 冒烟测试通过 |
| **构建** | Sphinx 8.1, ``build succeeded`` (0 warnings) |

## 子系统一览

```
 1.  架构总览
 2.  开发指南
 3.  对象模型 (15 篇)
 4.  字节码执行引擎 (6 篇)
 5.  编译系统 (6 篇)
 6.  内存管理 (4 篇)
 7.  并发与并行 (4 篇)
 8.  异常与调试 (4 篇)
 9.  模块系统 (3 篇)
10.  扩展与 C API (7 篇)
11.  运行时系统 (6 篇)
```

每章结构：**从一道题开始 → 通过示例脚本验证 → 小结 QA 表格 → 参考资料**

## 快速开始

```bash
# 安装依赖
pip install -e ".[dev]"

# （可选）拉取 CPython 源码对照阅读
git clone -b v3.14.5 https://github.com/python/cpython.git
export CPYTHON_SRC=$PWD/cpython

# 运行示例脚本
python examples/hello_pyobject.py

# 运行全部测试
make test

# 构建 HTML 文档
make docs
```

## 许可证

[MIT](LICENSE)
