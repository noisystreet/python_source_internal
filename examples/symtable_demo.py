"""符号表探针 — 观察 Python 名字的作用域分析。

演示内容：
  - 模块作用域
  - 函数局部作用域
  - global / nonlocal 声明
  - 闭包中的 FREE / CELL 变量
"""

import symtable


def analyze_scope(source: str, name: str = "<test>") -> symtable.SymbolTable:
    """创建符号表并打印信息。"""
    table = symtable.symtable(source, name, "exec")
    return table


def print_scope_info(table: symtable.SymbolTable, indent: str = "") -> None:
    """递归打印作用域信息。"""
    for name in table.get_symbols():
        flags = {
            "is_global": name.is_global(),
            "is_local": name.is_local(),
            "is_free": name.is_free(),
            "is_parameter": name.is_parameter(),
            "is_imported": name.is_imported(),
            "is_assigned": name.is_assigned(),
            "is_referenced": name.is_referenced(),
        }
        active = [k for k, v in flags.items() if v]
        print(f"{indent}  {name.get_name()}: {', '.join(active)}")

    for child in table.get_children():
        print(f"\n{indent}  [子作用域: {child.get_name()}]")
        print_scope_info(child, indent + "  ")


def main() -> None:
    print("=" * 60)
    print("符号表探针")
    print("=" * 60)

    # ── 1. 基本作用域 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 基本作用域")
    print("=" * 60)

    source = """
X = 10  # 模块级变量

def f():
    y = 20  # 局部变量
    print(y)
"""
    table = analyze_scope(source)
    print_scope_info(table)

    # ── 2. global 声明 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. global 声明")
    print("=" * 60)

    source = """
def f():
    global x
    x = 100
"""
    table = analyze_scope(source)
    print_scope_info(table)

    # ── 3. 闭包 ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 闭包变量 (FREE / CELL)")
    print("=" * 60)

    source = """
def outer():
    x = 10
    def inner():
        return x
    return inner
"""
    table = analyze_scope(source)
    print_scope_info(table)

    # ── 4. nonlocal ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("4. nonlocal 声明")
    print("=" * 60)

    source = """
def outer():
    x = 10
    def inner():
        nonlocal x
        x = 20
    inner()
"""
    table = analyze_scope(source)
    print_scope_info(table)

    # ── 5. 列表推导式作用域 ────────────────────────────────
    print("\n" + "=" * 60)
    print("5. 列表推导式作用域")
    print("=" * 60)

    source = """
x = [i * 2 for i in range(10)]
"""
    table = analyze_scope(source)
    print_scope_info(table)


if __name__ == "__main__":
    main()
