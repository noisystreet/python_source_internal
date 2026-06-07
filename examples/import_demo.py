"""导入机制探针 — 观察 Python 模块的导入流程。

演示内容：
  - sys.modules 缓存
  - 导入前后对比
  - 查找路径
  - 模块的字节码
"""

import dis
import sys


def main() -> None:
    print("=" * 60)
    print("导入机制探针")
    print("=" * 60)

    # ── 1. sys.modules 缓存 ────────────────────────────────
    print("\n" + "=" * 60)
    print("1. sys.modules 缓存")
    print("=" * 60)

    modules = ['sys', 'math', 'os', 'json', 'collections', 'pathlib']
    for name in modules:
        loaded = name in sys.modules
        print(f"  {name:>15}: {'已导入' if loaded else '未导入'}")

    # ── 2. 导入前后对比 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 导入前后对比")
    print("=" * 60)

    print(f"  导入前 'json' in sys.modules: {'json' in sys.modules}")
    import json
    print(f"  导入后 'json' in sys.modules: {'json' in sys.modules}")
    print(f"  json.__name__: {json.__name__}")
    print(f"  json.__file__: {json.__file__}")

    # ── 3. sys.path ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 查找路径 (sys.path)")
    print("=" * 60)

    for p in sys.path[:5]:
        print(f"  {p}")
    if len(sys.path) > 5:
        print(f"  ... 共 {len(sys.path)} 项")

    # ── 4. import 的字节码 ────────────────────────────────
    print("\n" + "=" * 60)
    print("4. import 字节码")
    print("=" * 60)

    def import_math():
        import math
        return math.pi

    dis.dis(import_math)


if __name__ == "__main__":
    main()
