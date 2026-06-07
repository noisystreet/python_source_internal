"""AST 探针 — 演示 AST 的结构、遍历和操作。

演示内容：
  - AST 节点统计
  - AST 节点位置信息
  - 遍历和修改 AST
"""

import ast


def count_nodes(tree: ast.AST) -> dict:
    counts = {}
    for node in ast.walk(tree):
        name = node.__class__.__name__
        counts[name] = counts.get(name, 0) + 1
    return counts


class FunctionCollector(ast.NodeVisitor):
    """收集所有函数定义。"""
    def __init__(self):
        self.functions = []

    def visit_FunctionDef(self, node):  # noqa: N802
        self.functions.append(node.name)
        self.generic_visit(node)


def main() -> None:
    print("=" * 60)
    print("AST 探针")
    print("=" * 60)

    source = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

result = factorial(10)
print(result)
"""
    tree = ast.parse(source)

    # ── 1. 节点统计 ────────────────────────────────────
    print("\n1. AST 节点统计")
    counts = count_nodes(tree)
    total = sum(counts.values())
    print(f"  总节点数: {total}")
    for name, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"    {name}: {count}")

    # ── 2. 收集函数名 ──────────────────────────────────
    print("\n2. 收集函数定义")
    collector = FunctionCollector()
    collector.visit(tree)
    print(f"  函数: {collector.functions}")

    # ── 3. 节点位置信息 ────────────────────────────────
    print("\n3. 节点位置信息")
    for node in ast.walk(tree):
        if hasattr(node, 'lineno'):
            name = node.__class__.__name__
            end = getattr(node, 'end_lineno', node.lineno)
            print(f"    {name:>15}: ({node.lineno}-{end})")


if __name__ == "__main__":
    main()
