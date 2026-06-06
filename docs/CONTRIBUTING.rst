贡献指南
========

感谢你对 python-source-internal 的关注！本文档说明如何参与贡献。

贡献方式
--------

* **提交 Issue**：发现文档错误、遗漏或建议新主题
* **提交 PR**：修正内容或新增解读章节
* **示例脚本**：为已有解读文档补充可运行的验证脚本

开发流程
--------

1. Fork 本仓库并克隆到本地
2. 阅读 `AGENTS.md <../AGENTS.md>`_ 了解编码约定
3. 创建分支：``git checkout -b topic/your-topic``
4. 按 :ref:`编码约定 <coding-conventions>` 编写内容
5. 确保 ``make lint test`` 通过
6. 提交 PR

文档规范
--------

* 使用中文撰写，关键术语首次出现时标注英文原文（如「对象 (``PyObject``)」）
* 代码块需标注语言（如 ``.. code-block:: python``、``.. code-block:: c``）
* 内部链接使用相对路径
* 新增文档需同步更新 :doc:`ARCHITECTURE` 索引

.. _coding-conventions:

编码约定
--------

见 `AGENTS.md <../AGENTS.md>`_。

安全政策
--------

安全相关问题 **不要** 在公开 Issue 中报告，请见 :doc:`SECURITY`。

许可证
------

本仓库使用 MIT 许可证（`LICENSE <../LICENSE>`_）。提交贡献即视为同意在相同许可证下发布。
