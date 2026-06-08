.. _compiler-deferred-annotations:

PEP 649 — 延迟注解评估
================================

.. epigraph::

   "Never put off till tomorrow what you can do today."

   -- Thomas Jefferson (ironically inverted for deferred evaluation)


PEP 649 是 Python 3.14 中引入的最重要的语法变更之一。
它改变了 **类型注解的评估时机**——从定义时立即评估推迟到需要时才评估。

从一道题开始
------------

.. code-block:: python

    # Python 3.13 及更早：注解在定义时立即评估
    def f(x: int) -> str:
        ...

    # Python 3.14+（PEP 649）：注解被延迟，不会立即执行

    def f(x: some_module.SomeType) -> None:
        ...
    # 3.14- 这里如果 some_module 还没 import → NameError
    # 3.14+ 不会报错，注解在首次访问 f.__annotations__ 时才评估

第一问：PEP 563 vs PEP 649
--------------------------

PEP 563（ ``from __future__ import annotations`` ）将所有注解变为字符串，
牺牲了运行时访问注解类型的能力。PEP 649 是更好的方案：

.. list-table::
   :header-rows: 1

   * - 特性
     - PEP 563（字符串化）
     - PEP 649（延迟评估）
   * - 何时评估？
     - NEVER（永远是字符串）
     - 首次访问 ``__annotations__`` 时
   * - ``get_type_hints()``
     - 需要 ``typing`` 解析字符串
     - 直接返回原始类型
   * - 运行时访问
     - ❌ 无法直接获取类型
     - ✅ 可见真实的类型对象
   * - 性能
     - 首次访问时无开销
     - 首次访问时计算

第二问：C 层的实现
------------------

PEP 649 的核心是在 ``PyCodeObject`` 中新增 ``co_annotation_events`` 字段。
注解不再作为常量编译，而是编译为一段 **延迟执行的字节码片段** ：

.. code-block:: c

    // Include/cpython/code.h
    typedef struct {
        // ... 原有字段 ...
        PyObject *co_annotation_events;  // 新增：注解执行事件表
    } PyCodeObject;

编译器生成注解的处理方式发生了变化：

.. mermaid::

    flowchart TD
        subgraph 旧方式["3.13- 立即评估"]
            compile_old["compile.c 遇到注解"] --> eval_old["编译为 LOAD_CONST<br/>consts 中已评估的值"]
        end
        subgraph 新方式["3.14+ 延迟评估"]
            compile_new["compile.c 遇到注解"] --> defer["生成注解字节码<br/>存入 co_annotation_events"]
            defer --> access["首次访问 __annotations__ 时"]
            access --> run["按需执行注解字节码"]
            run --> cache["缓存结果"]
        end

.. code-block:: c

    // compile.c 中的大致流程（简化）
    static int compiler_annotation(struct compiler *c, ...) {
    #ifdef PY_ANNOTATIONS_DEFERRED
        // PEP 649: 将注解编译为延迟代码块
        return compiler_deferred_annotation(c, annotation);
    #else
        // 旧方式：立即编译为常量
        return compiler_constant(c, annotation);
    #endif
    }

第三问：对开发者意味着什么
--------------------------

**前向引用不再需要引号包裹：**

.. code-block:: python

    # 3.14+ ✅ 直接写类型名，即使尚未定义
    class Tree:
        def get_child(self) -> Tree | None:  # Tree 在之后定义
            ...

        # 3.13- ❌ 必须写成 "Tree"（字符串注解）
        # 或 from __future__ import annotations

**数据类/基类不再需要 ``from __future__ import annotations`` ：**

.. code-block:: python

    from dataclasses import dataclass

    @dataclass
    class Node:
        children: list[Node]  # 3.14+ ✅ 直接引用自身
        value: int

PEP 649 在 ``dataclasses`` 、 ``pydantic`` 等依赖运行时类型分析的
库中影响最大——它们不再需要 ``from __future__`` 来解决前向引用问题。

通过示例脚本验证
----------------

运行 :file:`examples/annotation_demo.py`。

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - PEP 649 改变了什么？
     - 注解从定义时评估改为首次访问时评估
   * - 和 PEP 563 的区别？
     - PEP 563 永远存字符串，PEP 649 按需评估保留类型
   * - C 层怎么实现的？
     - co_annotation_events 字段 + 延迟字节码片段
   * - 3.14 项目需要改代码吗？
     - 不需要，向后兼容。但可以移除 ``from __future__ import annotations``
   * - 最大受益者？
     - 数据类、pydantic、FastAPI 等运行时依赖注解的库

参考资料
--------

- :pep:`649` — Deferred Evaluation Of Annotations Using Descriptors
- :pep:`563` — Postponed Evaluation of Annotations
- :file:`Objects/descrobject.c` — annotation 描述符实现
- :file:`Python/compile.c` — co_annotation_events 生成
- :file:`Python/ceval.c` — 延迟字节码的执行
- `PEP 649 解释器邮件列表讨论 <https://discuss.python.org/t/pep-649-deferred-evaluation-of-annotations/>`__
