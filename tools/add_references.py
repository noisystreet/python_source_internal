"""为 15 个核心章节添加参考资料。"""

import os

BASE = os.path.join(os.path.dirname(__file__), "..", "docs")

# 每个章节的参考资料内容
# 键：相对路径，值：(参考资料文本, 插入位置标志)
# 插入位置: "after_summary" = 接在 list-table 下方, "before_next" = 接在 "下一步" 之前
REFERENCES = {
    "objects/pyobject.rst": (
"""
参考资料
--------

- :pep:`683` — 永生对象（Immortal Objects）
- :file:`Include/object.h` — ``PyObject`` 与 ``PyVarObject`` 结构定义
- :file:`Include/refcount.h` — 引用计数宏实现
- `CPython 对象内存布局 <https://docs.python.org/3/c-api/structures.html>`__
""",
        "after_summary",
    ),
    "objects/typeobject.rst": (
"""
参考资料
--------

- :pep:`252` — 类型系统与描述符协议
- :pep:`573` — 模块级状态的 C 访问
- :file:`Include/object.h` — ``PyTypeObject`` 结构定义
- :file:`Objects/typeobject.c` — 类型创建与 MRO 计算
""",
        "before_next",
    ),
    "objects/refcount.rst": (
"""
参考资料
--------

- :pep:`683` — 永生对象
- :pep:`703` — 自由线程与平衡引用计数（BRC）
- :file:`Include/refcount.h` — ``Py_INCREF`` / ``Py_DECREF`` 实现
- :file:`Include/object.h` — ``ob_refcnt`` 与 ``ob_refcnt_shared`` 字段
""",
        "before_next",
    ),
    "objects/dict.rst": (
"""
参考资料
--------

- :pep:`509` — dict 的私有版本号
- :file:`Objects/dictobject.c` — dict 完整实现
- :file:`Include/cpython/dictobject.h` — ``PyDictKeysObject`` 结构定义
- `GH-26164 <https://github.com/python/cpython/issues/26164>`__ — 分离表与共享键
""",
        "after_summary",
    ),
    "objects/long.rst": (
"""
参考资料
--------

- :file:`Include/longintrepr.h` — ``PyLongObject`` 内部表示（digit / lv_tag）
- :file:`Objects/longobject.c` — 大整数运算实现
- `Knuth, The Art of Computer Programming, Vol. 2` — 多精度算术算法
""",
        "after_summary",
    ),
    "ceval/ceval-loop.rst": (
"""
参考资料
--------

- :pep:`659` — 自适应解释器（特化与内联缓存）
- :file:`Python/ceval.c` — Tier 1 主循环
- :file:`Python/ceval_macros.h` — ``DISPATCH`` / ``GOTO_*`` 宏
- `CPython 3.14 ceval 设计文档 <https://docs.python.org/3.14/howto/ceval.html>`__
""",
        "after_summary",
    ),
    "ceval/specialize.rst": (
"""
参考资料
--------

- :pep:`659` — 自适应特化
- :file:`Python/ceval.c` — 特化缓存的维护与失效
- :file:`Python/specialize.c` — 特化逻辑实现
- `GH-28676 <https://github.com/python/cpython/issues/28676>`__ — 内联缓存设计
""",
        "after_summary",
    ),
    "ceval/tier2.rst": (
"""
参考资料
--------

- :pep:`659` — 自适应解释器
- :file:`Python/ceval.c` — ``_PyEval_EvalDefault``（Tier 2 入口）
- :file:`Python/optimizer.c` — 优化器实现
- `GH-104584 <https://github.com/python/cpython/issues/104584>`__ — Tier 2 微码
""",
        "after_summary",
    ),
    "ceval/jit.rst": (
"""
参考资料
--------

- :file:`Python/jit.c` — Copy-and-Patch JIT 编译器
- :file:`Python/jit_allocator.c` — 机器码内存分配
- `GH-113464 <https://github.com/python/cpython/issues/113464>`__ — JIT 编译器设计
- `Copy-and-Patch 论文 <https://dl.acm.org/doi/10.1145/3485513>`__ — 原始论文 (SSW 2021)
""",
        "after_summary",
    ),
    "compiler/parser.rst": (
"""
参考资料
--------

- :pep:`617` — PEG 解析器
- :file:`Parser/python.gram` — PEG 语法规则文件
- :file:`Parser/pegen.c` — PEG 解析器实现
- `PEG 解析器设计文档 <https://peps.python.org/pep-0617/>`__
""",
        "after_summary",
    ),
    "compiler/tokenizer.rst": (
"""
参考资料
--------

- :pep:`701` — f-string 标记化
- :file:`Parser/lexer/` — tokenizer 实现目录
- :file:`Parser/lexer/state.h` — ``tok_state`` 结构定义
- `CPython 3.14 词法分析器说明 <https://docs.python.org/3.14/reference/lexical_analysis.html>`__
""",
        "after_summary",
    ),
    "gc/gc.rst": (
"""
参考资料
--------

- :pep:`442` — 安全终结的行为模型
- :file:`Python/gc.c` — GC 收集器实现
- :file:`Include/internal/pycore_gc.h` — GC 内部结构
- `Uniprocessor Garbage Collection Techniques <https://www.cs.utah.edu/~mflatt/papers/iwmm92.pdf>`__ — 分代 GC 基础论文
""",
        "after_summary",
    ),
    "gc/gc-cycles.rst": (
"""
参考资料
--------

- :file:`Python/gc.c` — ``deduce_unreachable`` 实现
- :file:`Include/internal/pycore_gc.h` — ``PyGC_Head`` 结构
- `三色标记算法 <https://en.wikipedia.org/wiki/Tracing_garbage_collection#Tri-color_marking>`__
""",
        "after_summary",
    ),
    "concurrency/gil.rst": (
"""
参考资料
--------

- :pep:`703` — 自由线程（无 GIL）
- :file:`Python/ceval_gil.c` — GIL 的 take / drop 实现
- `GIL 切换间隔 <https://docs.python.org/3/library/sys.html#sys.setswitchinterval>`__
- `Python GIL 的历史 <https://realpython.com/python-gil/>`__
""",
        "after_summary",
    ),
    "concurrency/free-threading.rst": (
"""
参考资料
--------

- :pep:`703` — 自由线程 CPython
- :file:`Python/ceval_gil.c` — ``--disable-gil`` 构建的 GIL 省略
- :file:`Include/internal/pycore_atomic.h` — 原子操作 API
- :file:`Objects/object.c` — BRC 平衡引用计数实现
""",
        "after_summary",
    ),
}


def main():
    for relpath, (ref_text, mode) in REFERENCES.items():
        path = os.path.join(BASE, relpath)
        with open(path) as f:
            content = f.read()

        if "参考资料" in content:
            print(f"  SKIP (already has): {relpath}")
            continue

        if mode == "before_next":
            # 在 "下一步" 之前插入
            marker = "下一步"
            idx = content.rfind(marker)
            if idx == -1:
                print(f"  ERROR (no '下一步' in): {relpath}")
                continue
            content = content[:idx] + ref_text + "\n" + content[idx:]
        else:
            # "after_summary": 追加到文件末尾
            content = content.rstrip() + "\n\n" + ref_text.lstrip() + "\n"

        with open(path, "w") as f:
            f.write(content)

        print(f"  ADDED: {relpath}")

    print("\nDone.")


if __name__ == "__main__":
    main()
