"""模块对象探针 — 观察 PyModuleObject。

演示内容：
  - 模块的 __dict__
  - 模块属性
"""

import math
import sys


def main() -> None:
    print("=" * 60)
    print("模块对象探针")
    print("=" * 60)

    print("\n--- math 模块 ---")
    print(f"  math.__name__: {math.__name__}")
    print(f"  math.__dict__ 有 {len(math.__dict__)} 项")

    print(f"\n  sys.modules['math'] is math: {sys.modules['math'] is math}")


if __name__ == "__main__":
    main()
