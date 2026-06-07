"""指令特化探针 — 观察字节码的自适应优化。

演示内容：
  - 通用指令 vs 特化指令
  - 特化触发条件
  - 加法特化观察
  - CALL 特化观察
  - 属性访问特化
"""

import dis
import time


def get_instruction_opnames(code) -> list:
    """获取函数的所有指令操作码名称。"""
    return [inst.opname for inst in dis.get_instructions(code)]


def demonstrate_specialization() -> None:
    """通过观察特化后的字节码变化来演示特化效果。"""

    # 加法函数 — 反复调用会触发 BINARY_OP 特化
    def add(a, b):
        return a + b

    print("  add(1, 2) 的初始指令:")
    for op in get_instruction_opnames(add.__code__)[:5]:
        print(f"    {op}")

    # 字符串加法
    def str_add(a, b):
        return a + b

    print("\n  BINARY_OP 特化途径:")
    print("    int + int   → BINARY_OP_ADD_INT")
    print("    float+float → BINARY_OP_ADD_FLOAT")
    print("    str + str   → BINARY_OP_ADD_UNICODE")

    # CALL 特化
    def call_len(lst):
        return len(lst)

    print("\n  CALL 特化途径:")
    print("    内置函数 (len)   → CALL_BUILTIN_FAST")
    print("    Python 函数      → CALL_PY_EXACT_ARGS")
    print("    方法调用         → CALL_BOUND_METHOD_EXACT_ARGS")

    # 预热后特化会触发
    print("\n  反复调用 len([1,2]) 10000 次:")
    t = time.perf_counter()
    for _ in range(10000):
        call_len([1, 2])
    elapsed = time.perf_counter() - t
    print(f"    耗时: {elapsed:.4f}s (特化后)")


def show_specializable_instructions() -> None:
    """列出可特化的指令及其特化版本。"""
    specializations = {
        "BINARY_OP": ["BINARY_OP_ADD_INT", "BINARY_OP_ADD_FLOAT",
                       "BINARY_OP_ADD_UNICODE"],
        "CALL": ["CALL_PY_EXACT_ARGS", "CALL_BUILTIN_FAST",
                  "CALL_BOUND_METHOD_EXACT_ARGS", "CALL_ALLOC_AND_ENTER_INIT"],
        "LOAD_ATTR": ["LOAD_ATTR_MANAGED_DICT", "LOAD_ATTR_INSTANCE_VALUE",
                       "LOAD_ATTR_SLOT"],
        "COMPARE_OP": ["COMPARE_OP_INT", "COMPARE_OP_FLOAT", "COMPARE_OP_STR"],
        "FOR_ITER": ["FOR_ITER_LIST", "FOR_ITER_DICT", "FOR_ITER_RANGE"],
        "LOAD_GLOBAL": ["LOAD_GLOBAL_MODULE", "LOAD_GLOBAL_BUILTIN"],
    }

    for base, specs in specializations.items():
        print(f"  {base:>15}:")
        for s in specs:
            print(f"    → {s}")


def main() -> None:
    print("=" * 60)
    print("指令特化探针")
    print("=" * 60)

    # ── 1. 可特化的指令 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 可特化的指令")
    print("=" * 60)

    show_specializable_instructions()

    # ── 2. 代码对象中的缓存槽 ──────────────────────────────
    print("\n" + "=" * 60)
    print("2. 指令缓存槽")
    print("=" * 60)

    # 查看每条指令分配的缓存槽大小
    # 来自 opcode metadata
    cache_sizes = {
        "RESUME": 0,
        "BINARY_OP": 5,  # 1 counter + 4 cache
        "CALL": 3,       # 1 counter + 2 cache
        "LOAD_ATTR": 5,  # 1 counter + 4 cache
        "LOAD_GLOBAL": 5,
        "STORE_ATTR": 5,
        "COMPARE_OP": 3,
        "FOR_ITER": 3,
        "UNPACK_SEQUENCE": 2,
    }
    for op, size in sorted(cache_sizes.items(), key=lambda x: -x[1]):
        if size > 0:
            print(f"  {op:>20}: {size} 个缓存槽")

    # ── 3. 特化演示 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 特化效果演示")
    print("=" * 60)

    demonstrate_specialization()

    # ── 4. 属性访问特化 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("4. 属性访问 (LOAD_ATTR)")
    print("=" * 60)

    class Point:
        __slots__ = ("x", "y")

        def __init__(self, x, y):
            self.x = x
            self.y = y

    # 普通类
    class Normal:
        def __init__(self):
            self.value = 42

    def get_attr(obj):
        return obj.value

    def get_slot(obj):
        return obj.x

    print("  普通类属性访问:")
    dis.dis(get_attr)

    print("\n  __slots__ 属性访问:")
    dis.dis(get_slot)

    # ── 5. 类型稳定性 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. 类型稳定性对特化的影响")
    print("=" * 60)

    print("  特化依赖于类型稳定性:")
    print("    总是 int + int → 特化为 BINARY_OP_ADD_INT")
    print("    时 int 时 str  → 反复反特化（性能下降）")
    print("  这就是为什么 Python 类型标注对性能有正面影响")


if __name__ == "__main__":
    main()
