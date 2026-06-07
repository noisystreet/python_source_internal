"""ceval 主循环探针 —— 观察字节码如何被解释执行。

演示内容：
  - 函数字节码反汇编
  - 评估栈的推入/弹出模拟
  - 帧链追踪
  - 异常传播路径
"""

import dis
import types


def show_op_stack(code: types.CodeType, *args):
    """模拟栈式虚拟机跟踪每条指令对栈的影响。"""
    print(f"\n--- 模拟执行: {code.co_name}{args} ---")

    # 模拟栈和局部变量
    stack = []
    # locals_dict 用索引定位（LOAD_FAST 的 arg 就是变量索引）
    locals_dict = {}

    # 将参数按索引赋值
    varnames = code.co_varnames
    for i, arg_val in enumerate(args):
        locals_dict[i] = arg_val
        print(f"  设置参数: {varnames[i]} = {arg_val}")

    # 简单模拟几条关键指令
    instructions = list(dis.get_instructions(code))
    i = 0
    while i < len(instructions):
        inst = instructions[i]
        opname = inst.opname
        arg = inst.arg

        if opname == "RESUME":
            print("  RESUME → 帧就绪")
            i += 1
            continue

        elif opname in ("LOAD_FAST", "LOAD_FAST_LOAD_FAST"):
            if opname == "LOAD_FAST":
                val = locals_dict.get(arg)
                if val is not None:
                    stack.append(val)
                    print(f"  LOAD_FAST {varnames[arg]} → 栈: {stack}")
            else:
                # LOAD_FAST_LOAD_FAST loads two fast vars
                # first index = arg >> 8, second = arg & 0xFF
                idx1 = arg >> 8
                idx2 = arg & 0xFF
                val1 = locals_dict.get(idx1)
                val2 = locals_dict.get(idx2)
                if val1 is not None:
                    stack.append(val1)
                if val2 is not None:
                    stack.append(val2)
                print(f"  LOAD_FAST_LOAD_FAST {varnames[idx1]}, "
                      f"{varnames[idx2]} → 栈: {stack}")
            i += 1

        elif opname == "LOAD_CONST":
            val = inst.argval if hasattr(inst, 'argval') else arg
            stack.append(arg)
            print(f"  LOAD_CONST {arg} → 栈: {stack}")
            i += 1

        elif opname == "BINARY_OP":
            b = stack.pop()
            a = stack.pop()
            result = a + b
            stack.append(result)
            print(f"  BINARY_OP + → {a} + {b} = {result}, 栈: {stack}")
            i += 1

        elif opname == "STORE_FAST":
            val = stack.pop()
            locals_dict[arg] = val
            print(f"  STORE_FAST {arg} = {val}, 栈: {stack}")
            i += 1

        elif opname == "RETURN_VALUE":
            result = stack.pop() if stack else None
            print(f"  RETURN_VALUE → {result}")
            return result

        else:
            print(f"  {opname} (跳过)")
            i += 1

    return None


def frame_stack_depth(code: types.CodeType) -> int:
    """计算函数执行过程中评估栈的最大深度。"""
    stack = 0
    max_depth = 0
    for inst in dis.get_instructions(code):
        opname = inst.opname
        effect = 0
        if opname.startswith("LOAD_"):
            if opname == "LOAD_FAST_LOAD_FAST":
                effect = 2
            else:
                effect = 1  # 压栈
        elif opname.startswith("STORE_") or opname == "RETURN_VALUE":
            effect = -1  # 弹栈
        elif opname.startswith("BINARY_") or opname.startswith("UNARY_"):
            effect = -1  # 弹出两个压入一个
        elif opname.startswith("CALL"):
            effect = -(inst.arg + 1) + 1  # 弹出参数和函数, 压入返回值

        stack += effect
        max_depth = max(max_depth, stack)

    return max_depth


def main() -> None:
    print("=" * 60)
    print("ceval 解释循环探针")
    print("=" * 60)

    # ── 1. 简单函数的字节码 ────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 函数字节码")
    print("=" * 60)

    def add(a, b):
        c = a + b
        return c

    print("\n  add(3, 5) 的字节码:")
    dis.dis(add)

    # ── 2. 栈模拟 ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 评估栈模拟")
    print("=" * 60)

    show_op_stack(add.__code__, 3, 5)

    # ── 3. 栈深度分析 ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 评估栈深度分析")
    print("=" * 60)

    def simple():
        return 42

    def nested_calls():
        return len(str(42))

    def complex_expression():
        return (1 + 2) * (3 + 4) - 5

    for fn in [simple, nested_calls, complex_expression]:
        depth = frame_stack_depth(fn.__code__)
        print(f"  {fn.__name__:>18}: 栈最大深度 = {depth}")

    # ── 4. 多个函数的帧链 ──────────────────────────────────
    print("\n" + "=" * 60)
    print("4. 帧调用链")
    print("=" * 60)

    def inner(x):
        return x * 2

    def outer(x):
        return inner(x + 1)

    print("  调用 outer(5):")
    result = outer(5)
    print(f"  outer(5) = {result}")
    print("  调用链: outer → inner → inner 返回 → outer 返回")
    print("  每个调用创建一个 _PyInterpreterFrame")

    # ── 5. 异常处理路径 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. try/except 的字节码")
    print("=" * 60)

    def try_except():
        try:
            1 / 0
        except ZeroDivisionError:
            return "caught"

    dis.dis(try_except)

    # ── 6. 字节码指令统计分析 ─────────────────────────────
    print("\n" + "=" * 60)
    print("6. 指令统计")
    print("=" * 60)

    def count_opcodes(code: types.CodeType):
        counts = {}
        for inst in dis.get_instructions(code):
            opname = inst.opname
            counts[opname] = counts.get(opname, 0) + 1
        return counts

    def fibonacci(n):
        if n < 2:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)

    counts = count_opcodes(fibonacci.__code__)
    print("  fibonacci 函数指令统计:")
    for opname, count in sorted(counts.items()):
        print(f"    {opname:>20}: {count}")
    print(f"  总计: {sum(counts.values())} 条指令")


if __name__ == "__main__":
    main()
