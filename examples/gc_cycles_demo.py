"""环形引用检测探针 — 模拟三色标记算法。

演示内容：
  - 对象引用图的可达性分析
  - gc_refs 计算
  - 循环引用检测的模拟
"""

import gc


class GCNode:
    """模拟被 GC 跟踪的对象。"""
    _all = []

    def __init__(self, name: str):
        self.name = name
        self.refs = []  # 引用的其他节点
        self._ref_by = []  # 被引用的来源
        self.gc_refs = 1
        GCNode._all.append(self)

    def __repr__(self):
        return self.name

    def add_ref(self, target):
        self.refs.append(target)
        target._ref_by.append(self)


def simulate_gc_cycle_detection():
    """模拟 GC 的 deducing_unreachable 算法。"""
    print("\n  --- 模拟: 三色标记 ---")

    # 创建引用图
    a = GCNode("A")
    b = GCNode("B")
    c = GCNode("C")

    a.add_ref(b)
    b.add_ref(c)
    c.add_ref(a)  # A → B → C → A 循环

    d = GCNode("D")
    e = GCNode("E")
    d.add_ref(e)  # D → E 无循环

    GCNode("F")  # 孤立

    # 模拟根引用 — 假设 A 和 D 被根引用
    roots = {a, d}

    print("  引用图: A→B→C→A (循环), D→E, F(孤立)")
    print("  根对象: A, D")

    # Step 1: init gc_refs = len(ref_by)
    for node in GCNode._all:
        node.gc_refs = len(node._ref_by)
        print(f"  初始 refcount({node.name}) = {node.gc_refs}")

    # Step 2: subtract external refs — 只有 roots 是外部的
    for node in GCNode._all:
        if node not in roots:
            # 减去来自 roots 的引用
            for ref_by in node._ref_by:
                if ref_by in roots:
                    node.gc_refs -= 1

    print("\n  减去外部引用后:")
    for node in GCNode._all:
        print(f"    gc_refs({node.name}) = {node.gc_refs}")

    # Step 3: propagate from gc_refs > 0
    reachable = set()
    worklist = [node for node in GCNode._all if node.gc_refs > 0]
    while worklist:
        node = worklist.pop()
        if node in reachable:
            continue
        reachable.add(node)
        for ref in node.refs:
            if ref not in reachable:
                worklist.append(ref)

    unreachable = set(GCNode._all) - reachable - roots

    print(f"\n  可达: {reachable}")
    print(f"  不可达(循环/孤立): {unreachable}")
    print(f"  → 将被回收的对象: {unreachable}")


def show_gc_stats():
    """展示当前 GC 状态。"""
    print(f"\n  GC 三代计数: {gc.get_count()}")
    print(f"  GC 阈值: {gc.get_threshold()}")
    print(f"  GC 是否启用: {gc.isenabled()}")


def main() -> None:
    print("=" * 60)
    print("环形引用检测探针")
    print("=" * 60)

    simulate_gc_cycle_detection()

    print("\n" + "=" * 60)
    print("GC 状态")
    print("=" * 60)
    show_gc_stats()


if __name__ == "__main__":
    # 清理模拟的全局状态
    main()
    GCNode._all.clear()
