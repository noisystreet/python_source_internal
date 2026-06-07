"""分代 GC 探针 — 观察垃圾回收器如何检测和回收循环引用。

演示内容：
  - 循环引用检测
  - 分代提升
  - __del__ 对 GC 的影响
  - gc 调试工具
"""

import gc


class Node:
    def __init__(self, name: str = ""):
        self.name = name
        self.next = None
        self.ref = None

    def __repr__(self):
        return f"Node({self.name})"


def main() -> None:
    print("=" * 60)
    print("分代 GC 探针")
    print("=" * 60)

    # ── 1. 循环引用检测 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 循环引用检测")
    print("=" * 60)

    gc.collect()  # 清理

    a = Node("A")
    b = Node("B")
    a.ref = b
    b.ref = a  # 循环引用

    del a
    del b

    collected = gc.collect()
    print(f"  gc.collect() 回收了 {collected} 个对象")

    # ── 2. 无循环引用 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 无循环引用 — 引用计数即时处理")
    print("=" * 60)

    gc.collect()

    x = Node("X")
    y = Node("Y")
    x.ref = y  # 单向引用，无循环
    del x
    del y

    print("  无循环引用，引用计数直接回收，GC 计数不变")

    # ── 3. 代际分布观察 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 代际分布观察")
    print("=" * 60)

    gc.collect()
    print(f"  初始: {gc.get_count()}")

    # 创建一些临时对象
    for i in range(100):
        n = Node(f"temp_{i}")
        n.next = Node(f"child_{i}")

    print(f"  创建 100 个临时对象后: {gc.get_count()}")

    # 收集第 0 代
    gc.collect(0)
    print(f"  收集第 0 代后: {gc.get_count()}")

    # ── 4. __del__ 对 GC 的影响 ────────────────────────────
    print("\n" + "=" * 60)
    print("4. __del__ 与 GC")
    print("=" * 60)

    class FinalizableNode:
        def __init__(self, name: str):
            self.name = name
            self.ref = None

        def __del__(self):
            pass

    gc.collect()
    a = FinalizableNode("A")
    b = FinalizableNode("B")
    a.ref = b
    b.ref = a
    del a
    del b

    collected = gc.collect()
    print(f"  有 __del__ 的循环引用: gc.collect() 回收了 {collected} 个")
    print("  这是 Python 3.14+ 的行为（以前版本可能无法回收）")

    # ── 5. get_referrers / get_referents ────────────────────
    print("\n" + "=" * 60)
    print("5. 引用追踪工具")
    print("=" * 60)

    obj = Node("target")
    lst = [obj]

    referrers = gc.get_referrers(obj)
    print(f"  gc.get_referrers(obj): 找到 {len(referrers)} 个引用者")
    for r in referrers:
        if isinstance(r, list):
            print("    - list (包含 obj)")

    referents = gc.get_referents(lst)
    print(f"  gc.get_referents(lst): 找到 {len(referents)} 个被引用对象")
    for r in referents:
        print(f"    - {type(r).__name__}")

    # ── 6. get_objects ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("6. gc.get_objects — 所有被跟踪的对象")
    print("=" * 60)

    all_objs = gc.get_objects()
    # 按类型统计
    type_counts = {}
    for obj in all_objs:
        type_counts[type(obj).__name__] = type_counts.get(type(obj).__name__, 0) + 1

    print(f"  被 GC 跟踪的对象总数: {len(all_objs)}")
    print("  前 10 种类型:")
    for tname, count in sorted(type_counts.items(),
                                key=lambda x: -x[1])[:10]:
        print(f"    {tname:>20}: {count}")


if __name__ == "__main__":
    main()
