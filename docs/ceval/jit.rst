JIT 编译器 — 从微码到机器码
==================================

CPython 3.14 包含一个实验性的 **复制并修补 (Copy-and-Patch) JIT 编译器**。
它从 Tier 2 微码生成原生机器码，实现接近 C 级别的执行速度。

从一道题开始
------------

从字节码到机器码的执行路径有三层：

.. code-block:: text

    Tier 1:  字节码 → 自适应解释器（逐条分发）
    Tier 2:  字节码 → 微码序列（批量执行）
    JIT:     微码 → 原生机器码（直连硬件）

每一层都对应一次性能提升，但优化的"预热"时间也更长。

.. mermaid::

    flowchart LR
        bc["字节码 (bytecode)"] -->|"Tier 1<br/>首次执行"| interp["自适应解释器<br/>~50M op/s"]
        bc -->|"循环触发"| opt["优化器"]
        opt -->|"Tier 2<br/>微码"| uop["微码执行器<br/>~150M op/s"]
        opt -->|"进一步编译"| jit_entry["JIT 编译器<br/>Copy-and-Patch"]
        jit_entry -->|"JIT<br/>机器码"| native["原生机器码<br/>~500M op/s"]

第一问：什么是 Copy-and-Patch JIT？
-----------------------------------

传统的 JIT 编译器（如 Java JIT）很复杂，需要包含完整的编译器和链接器。
Copy-and-Patch 是一种**轻量级 JIT 方案**：

#. **预编译模板**：每个微码指令对应一段预编译好的机器码模板
#. **复制**：将需要的模板复制到一起
#. **修补**：修补模板中的地址和常量（类似链接器的重定位）

.. code-block:: c

    // jit.c 中的编译入口
    int _PyJIT_Compile(_PyExecutorObject *executor,
                        const _PyUOpInstruction trace[],
                        size_t length)
    {
        // 1. 估算需要的机器码大小
        size_t code_size = jit_stub_size(...);

        // 2. 分配可执行内存
        void *code = mmap(NULL, code_size,
                          PROT_READ | PROT_WRITE | PROT_EXEC,
                          MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);

        // 3. 为每条微码复制 + 修补对应的机器码模板
        for (size_t i = 0; i < length; i++) {
            offset += jit_emit(&code, &trace[i]);
        }

        // 4. 设置执行器为 JIT 编译模式
        executor->jit_code = code;
        executor->jit_usable = true;
    }

编译后的机器码被替换到 executor 中，Tier 2 循环发现 ``_Py_JIT`` 定义后
直接跳转到机器码执行。

第二问：哪些代码会被 JIT 编译？
-------------------------------

JIT 编译发生在 Tier 2 优化之后。当 Tier 2 发现一个 executor 被频繁执行（"升温"）：

.. code-block:: c

    // optimizer.c 中
    executor->vm_data.warm = true;
    if (_PyJIT_Compile(executor, executor->trace, length)) {
        // JIT 编译失败 → 继续用 Tier 2 微码执行
        Py_DECREF(executor);
        return NULL;
    }
    // JIT 编译成功 → executor 现在会执行机器码

JIT 编译的触发条件：

- executor 已经**升温**（被多次执行）
- 微码序列长度合适（太短不值得编译，太长编译成本高）
- 平台支持（目前只支持 x86-64 和 ARM64）

第三问：JIT 编译的产物
----------------------

编译产物是一段**连续的原生机器码**：

.. code-block:: text

    内存布局：
    ┌──────────────────────────────────┐
    │  prologue（保存寄存器等）         │
    ├──────────────────────────────────┤
    │  LOAD_FAST 的机器码模板           │
    ├──────────────────────────────────┤
    │  LOAD_FAST 的机器码模板           │
    ├──────────────────────────────────┤
    │  BINARY_OP_ADD_INT 的机器码模板   │
    ├──────────────────────────────────┤
    │  STORE_FAST 的机器码模板          │
    ├──────────────────────────────────┤
    │  JUMP_BACKWARD 的机器码模板       │
    ├──────────────────────────────────┤
    │  epilogue（恢复寄存器等）         │
    └──────────────────────────────────┘

每段模板在复制时已经修补了具体的偏移量和地址。执行时不需要任何解释开销。

第四问：JIT 的安全与回落
------------------------

当代码对象的版本号变化（例如 ``func.__code__`` 被替换）时，JIT 编译的代码
**立即失效**。CPython 通过版本号检查确保安全性：

.. code-block:: c

    // 在执行 JIT 编译代码前检查版本号
    if (executor->co_version != code->co_version) {
        // 代码已变化，JIT 代码无效
        executor->jit_usable = false;
        // 回退到 Tier 1 重新执行
    }

如果 JIT 编译失败（内存不足、平台不支持），executor 无缝回退到 Tier 2
微码执行模式。

通过示例脚本验证
----------------

运行 :file:`examples/jit_demo.py`：

.. code-block:: text

    --- 执行路径对比 ---
    Tier 1:  LOAD_FAST → BINARY_OP → STORE_FAST × 10000
    Tier 2:  微码序列执行
    JIT:    原生机器码执行

    --- 预热曲线 ---
    首次: 慢（Tier 1 自适应）
    升温: 中（Tier 2 微码）
    热:   快（JIT 机器码）

小结
----

.. list-table::
   :header-rows: 1

   * - 问题
     - 答案
   * - JIT 编译器基于什么技术？
     - Copy-and-Patch：预编译模板 + 重定位修补
   * - JIT 从哪里获取输入？
     - Tier 2 优化器生成的微码序列
   * - 哪些代码会被 JIT 编译？
     - 升温的热路径 executor
   * - JIT 编译失败怎么办？
     - 回退到 Tier 2 微码执行
   * - 代码变化时 JIT 代码怎么处理？
     - 版本号检查，自动失效
   * - 支持哪些平台？
     - x86-64 和 ARM64

参考资料
--------

- :file:`Python/jit.c` — Copy-and-Patch JIT 编译器
- :file:`Python/jit_allocator.c` — 机器码内存分配
- `GH-113464 <https://github.com/python/cpython/issues/113464>`__ — JIT 编译器设计
- `Copy-and-Patch 论文 <https://dl.acm.org/doi/10.1145/3485513>`__ — 原始论文 (SSW 2021)

