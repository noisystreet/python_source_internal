"""Parser / AST 探针 — 观察 PEG 解析器和抽象语法树。

演示内容：
  - 使用 ast 模块查看 AST 结构
  - 不同语法结构的 AST
  - 语法错误报告
  - AST 节点类型统计
"""

import ast


def show_ast(source: str, mode: str = 'exec') -> None:
    """展示一段代码的 AST 树。"""
    print(f"\n  源码: {source!r}")
    try:
        tree = ast.parse(source, mode=mode)
        print(f"  AST: {ast.dump(tree, indent=2)}")
    except SyntaxError as e:
        print(f"  语法错误: {e}")


def count_ast_nodes(tree: ast.AST) -> dict:
    """统计 AST 中各类节点的数量。"""
    counts = {}
    for node in ast.walk(tree):
        name = node.__class__.__name__
        counts[name] = counts.get(name, 0) + 1
    return counts


def main() -> None:
    print("=" * 60)
    print("Parser / AST 探针")
    print("=" * 60)

    # ── 1. 表达式 AST ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 表达式 AST")
    print("=" * 60)

    show_ast('x + 42', 'eval')
    show_ast('a + b * c', 'eval')
    show_ast('f(x, y)', 'eval')
    show_ast('[1, 2, 3]', 'eval')
    show_ast('{"a": 1, "b": 2}', 'eval')

    # ── 2. 语句 AST ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 语句 AST")
    print("=" * 60)

    show_ast('if x:\n    pass')
    show_ast('for i in range(10):\n    print(i)')
    show_ast('try:\n    1/0\nexcept:\n    pass')

    # ── 3. 函数定义 AST ────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 函数定义 AST")
    print("=" * 60)

    show_ast("def f(x, y=10):\n    return x + y")

    # ── 4. 语法错误 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("4. 语法错误")
    print("=" * 60)

    bad_sources = [
        ("x = ", "不完整的赋值"),
        ("if x:", "缺少缩进块"),
        ("x = +* 2", "连续运算符"),
    ]
    for src, desc in bad_sources:
        print(f"\n  {desc} ({src!r}):")
        show_ast(src)

    # ── 5. AST 节点统计 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. AST 节点统计")
    print("=" * 60)

    source = """
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

result = fibonacci(10)
print(result)
"""
    tree = ast.parse(source)
    counts = count_ast_nodes(tree)
    total = sum(counts.values())
    print(f"  总共 {total} 个 AST 节点")
    for name, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"    {name:>20}: {count}")

    # ── 6. AST 节点类型一览 ────────────────────────────────
    print("\n" + "=" * 60)
    print("6. AST 节点类型")
    print("=" * 60)

    major_types = [
        "Module", "Expr", "Pass", "Assign", "If", "For", "While",
        "BinOp", "UnaryOp", "Name", "Constant", "Call", "FunctionDef",
        "ClassDef", "Return", "Try", "List", "Dict", "Tuple",
    ]
    for t in major_types:
        node_class = getattr(ast, t, None)
        if node_class:
            fields = [f[0] for f in ast.iter_fields(node_class)]
            print(f"  {t:>20}: 字段={fields}")
        else:
            print(f"  {t:>20}: (未知)")


if __name__ == "__main__":
    main()
