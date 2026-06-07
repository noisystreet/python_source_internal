"""核心字节码指令分析探针。

演示内容：
  - 不同函数的指令频次统计
  - 超指令观察 (LOAD_FAST_LOAD_FAST)
  - 指令分类分析
  - CALL 指令追踪
  - 条件跳转
"""

import collections
import dis
import types


def count_opcodes(code: types.CodeType) -> dict:
    """统计代码对象中各指令的出现次数。"""
    counts = collections.Counter()
    for inst in dis.get_instructions(code):
        counts[inst.opname] += 1
    return dict(counts)


def categorize_instructions(code: types.CodeType) -> dict:
    """按功能组分类指令。"""
    categories = {
        "load_store": 0,    # 加载/存储
        "binary": 0,        # 运算
        "call": 0,          # 调用
        "control": 0,       # 流程控制
        "other": 0,         # 其他
    }

    load_store = {"LOAD_FAST", "STORE_FAST", "LOAD_CONST", "LOAD_GLOBAL",
                  "LOAD_FAST_LOAD_FAST", "STORE_FAST_LOAD_FAST",
                  "LOAD_DEREF", "STORE_DEREF"}
    binary_ops = {"BINARY_OP", "UNARY_NEGATIVE", "UNARY_NOT"}
    call_ops = {"CALL", "CALL_FUNCTION_EX", "CALL_METHOD", "PUSH_NULL",
                "LOAD_METHOD"}
    control_ops = {"JUMP_FORWARD", "JUMP_BACKWARD", "POP_JUMP_IF_TRUE",
                   "POP_JUMP_IF_FALSE", "RETURN_VALUE", "RESUME",
                   "FOR_ITER", "JUMP_IF_TRUE_OR_POP", "JUMP_IF_FALSE_OR_POP"}

    for inst in dis.get_instructions(code):
        if inst.opname in load_store:
            categories["load_store"] += 1
        elif inst.opname in binary_ops:
            categories["binary"] += 1
        elif inst.opname in call_ops:
            categories["call"] += 1
        elif inst.opname in control_ops:
            categories["control"] += 1
        else:
            categories["other"] += 1

    return categories


def dis_with_line_numbers(code: types.CodeType) -> None:
    """带函数名的反汇编输出。"""
    for inst in dis.get_instructions(code):
        offset = inst.offset
        opname = inst.opname
        arg = inst.argrepr if inst.argrepr else ""
        print(f"  {offset:>4} {opname:>30} {arg}")


def main() -> None:
    print("=" * 60)
    print("核心字节码指令分析")
    print("=" * 60)

    # ── 1. 指令频次统计 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 指令频次统计")
    print("=" * 60)

    def add(a, b):
        return a + b

    def factorial(n):
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result

    def fibonacci(n):
        if n < 2:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)

    for fn in [add, factorial, fibonacci]:
        counts = count_opcodes(fn.__code__)
        categories = categorize_instructions(fn.__code__)
        total = sum(counts.values())
        print(f"\n  {fn.__name__:>10}: 总计 {total:>2} 条指令")
        for opname, count in sorted(counts.items()):
            print(f"    {opname:>30}: {count}")
        print(f"    {'类别':>30}: {categories}")

    # ── 2. 超指令观察 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 超指令 (LOAD_FAST_LOAD_FAST)")
    print("=" * 60)

    def multi_load(a, b, c, d):
        return a + b + c + d

    print("\n  multi_load(a, b, c, d):")
    dis_with_line_numbers(multi_load.__code__)

    # ── 3. 条件与循环 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 条件与循环指令")
    print("=" * 60)

    def classify(x):
        if x < 0:
            return "negative"
        elif x == 0:
            return "zero"
        else:
            return "positive"

    def count_down(n):
        result = []
        while n > 0:
            result.append(n)
            n -= 1
        return result

    for fn in [classify, count_down]:
        print(f"\n  {fn.__name__}:")
        dis_with_line_numbers(fn.__code__)

    # ── 4. 函数调用链 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("4. 函数调用指令")
    print("=" * 60)

    def caller():
        return inner(1, 2, 3)

    def inner(a, b, c):
        return a + b + c

    print("\n  caller (调用指令):")
    dis_with_line_numbers(caller.__code__)

    print("\n  inner (被调用):")
    dis_with_line_numbers(inner.__code__)

    # 参数个数统计
    def f0(): pass
    def f1(a): pass
    def f2(a, b): pass
    def f3(a, b, c): pass

    for fn in [f0, f1, f2, f3]:
        code = fn.__code__
        print(f"  {fn.__name__}: co_argcount={code.co_argcount}, "
              f"co_nlocals={code.co_nlocals}")

    # ── 5. BINARY_OP 的操作码参数 ──────────────────────────
    print("\n" + "=" * 60)
    print("5. BINARY_OP 的操作码")
    print("=" * 60)

    # 查看 BINARY_OP 的 oparg 值
    def ops():
        return (3 + 5, 10 - 3, 7 * 8, 17 // 3, 17 % 3)

    for inst in dis.get_instructions(ops):
        if inst.opname == "BINARY_OP":
            oparg = inst.arg
            op_names = {0: "ADD", 1: "SUBTRACT", 2: "MULTIPLY",
                        3: "REMAINDER", 4: "DIVIDE", 5: "FLOOR_DIVIDE"}
            name = op_names.get(oparg, "?")
            print(f"  BINARY_OP oparg={oparg} → {name}")

    # ── 6. COMPARE_OP ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("6. COMPARE_OP 的比较类型")
    print("=" * 60)

    def comparisons(x, y):
        return (x < y, x <= y, x == y, x != y, x > y, x >= y)

    for inst in dis.get_instructions(comparisons):
        if inst.opname == "COMPARE_OP":
            print(f"  COMPARE_OP oparg={inst.arg} → {inst.argrepr}")


if __name__ == "__main__":
    main()
