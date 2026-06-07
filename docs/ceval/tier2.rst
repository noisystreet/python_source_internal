Tier 2 优化器 — 热路径的微码优化
========================================

CPython 3.14 引入了**双层解释器架构** ：

- **Tier 1** ：逐条执行字节码的自适应解释器
- **Tier 2** ：将热路径（hot path）编译为微码（uop），批量执行

从一道题开始
------------

Tier 2 的核心思想：**不是所有代码执行频率都相同** 。大约 90% 的执行时间花在 10% 的代码上。
Tier 2 优化器专门针对这 10% 的"热路径"做优化。

.. code-block:: text

    执行路径示例：
    LOAD_FAST → LOAD_FAST → BINARY_OP → STORE_FAST → JUMP_BACKWARD

    Tier 1: 逐条执行，每条指令都要查表分发 × 5 次
    Tier 2: 编译为微码序列，单次进入批量执行

第一问：从 Tier 1 到 Tier 2 的切换
-----------------------------------

当 Tier 1 解释器检测到**循环体执行超过一定次数**时：

.. code-block:: c

    // 在 JUMP_BACKWARD 指令中
    TARGET(JUMP_BACKWARD) {
        // ...
        // 检测热循环
        if (--loop_counter <= 0) {
            // 触发优化
            _Py_Optimize(tstate, frame, next_instr);
        }
        // ...
    }

``_Py_Optimize`` 调用优化器，尝试将当前执行片段编译为 Tier 2 微码序列生成器
（executor）。成功后会设置 ``tstate->current_executor`` 。

下次进入解释循环时，检测到 ``current_executor`` ：

.. code-block:: c

    // _PyEval_EvalFrameDefault 开头
    if (tstate->current_executor != NULL) {
        entry.frame.localsplus[0] = current_executor;
        tstate->current_executor = NULL;
        // 跳转到 Tier 2 入口
    }

.. mermaid::

    flowchart LR
        tier1["Tier 1 解释器<br/>逐条执行字节码"] --> hot{"循环次数 > 阈值?"}
        hot -->|"否"| tier1
        hot -->|"是"| optimizer["_Py_Optimize<br/>编译热路径为微码"]
        optimizer --> tier2["Tier 2 执行器<br/>批量执行微码序列"]
        tier2 -->|"执行完毕"| tier1
        tier2 -->|"反优化触发"| tier1

第二问：微码 (Micro-ops) 是什么？
---------------------------------

微码是比字节码更低级的指令。每条字节码可以拆成若干条微码：

.. code-block:: text

    LOAD_FAST  a   →  _LOAD_FAST  1
    LOAD_FAST  b   →  _LOAD_FAST  2
    BINARY_OP  +   →  _BINARY_OP_ADD_INT
    STORE_FAST c   →  _STORE_FAST 3
    JUMP_BACKWARD  →  _JUMP_BACKWARD

微码的优势：

- **更细粒度** ：可以跳过通用检查（类型检查、边界检查）
- **更紧凑** ：执行循环比字节码分发快
- **可以内联** ：函数调用边界可以在微码中消除

Tier 2 的执行器是一个简单的循环：

.. code-block:: c

    // ceval.c 中的 Tier 2 主循环
    enter_tier_two:
        for (;;) {
            uopcode = next_uop->opcode;
            next_uop++;
            switch (uopcode) {
                #include "executor_cases.c.h"
            }
        }

``executor_cases.c.h`` 是由工具自动生成的，包含所有微码指令的实现。

第三问：优化器的缓存策略
------------------------

优化后的 executor 会被**缓存到代码对象**中：

.. code-block:: c

    // PyCodeObject 中的 executor 缓存
    struct PyCodeObject {
        // ...
        _PyExecutorArray *co_executors;  // ★ Tier 2 executor 缓存
        // ...
    };

当代码对象被修改（例如通过 ``__code__`` 赋值）时，executor 缓存会被清空。
executor 的版本号与代码对象的 ``co_version`` 绑定。

在自由线程构建中，每个线程还有线程本地的字节码副本（``co_tlbc`` ），
避免了多线程下的锁竞争。

第四问：Tier 2 能做什么 Tier 1 做不到的优化？
-----------------------------------------------

**1. 循环不变代码外提**
  Tier 2 可以将循环内不随迭代变化的操作提取到循环外执行。

**2. 常量折叠**
  字节码中未曾折叠的常量操作可以在微码中完成。

**3. 类型特化传播**
  Tier 1 对单个指令做特化；Tier 2 可以在一条路径上传播类型信息。
  例如：如果 ``LOAD_FAST a`` 加载的总是 ``int``，后续的 ``BINARY_OP``
  可以直接使用整数加法微码。

**4. 内联函数调用**
  对于小函数，Tier 2 可以将其调用展开到当前路径中，省去帧创建的开销。

通过示例脚本验证
----------------

运行 :file:`examples/tier2_demo.py`：

.. code-block:: text

    --- 热循环检测 ---
    循环 10000 次 → 触发 Tier 2 优化
    循环 1 次 → 不触发

    --- 路径追踪 ---
    简单循环的字节码序列被编译为微码

    --- 性能对比 ---
    第一次运行（Tier 1）: 0.0021s
    后面运行（Tier 2）: 0.0008s

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - Tier 1 做什么？
     - 逐条执行字节码，做指令级特化
   * - Tier 2 做什么？
     - 将热路径编译为微码序列批量执行
   * - 什么时候切到 Tier 2？
     - 循环超过阈值时
   * - 微码是什么？
     - 比字节码更底层的指令，一个字节码拆成多个微码
   * - Tier 2 能做什么额外优化？
     - 循环外提、内联调用、类型传播
   * - Executor 存在哪？
     - 代码对象的 co_executors 字段

参考资料
--------

- :pep:`659` — 自适应解释器
- :file:`Python/ceval.c` — ``_PyEval_EvalDefault`` （Tier 2 入口）
- :file:`Python/optimizer.c` — 优化器实现
- `GH-104584 <https://github.com/python/cpython/issues/104584>`__ — Tier 2 微码

