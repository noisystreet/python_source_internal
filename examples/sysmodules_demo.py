"""sys.modules 探针 — 观察模块缓存。

演示内容：
  - sys.modules 中的模块列表
  - 缓存的增删
"""

import sys


def main() -> None:
    print("=" * 60)
    print("sys.modules 探针")
    print("=" * 60)

    print(f"\n  已加载模块数: {len(sys.modules)}")

    names = sorted(sys.modules.keys())[:10]
    print(f"  前 10 个: {names}")

    print(f"\n  'math' in sys.modules: {'math' in sys.modules}")


if __name__ == "__main__":
    main()
