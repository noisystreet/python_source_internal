"""调试支持探针 — 观察 sys.breakpointhook。

演示内容：
  - breakpoint() 函数
  - sys.breakpointhook
"""

import sys


def main() -> None:
    print("=" * 60)
    print("调试支持探针")
    print("=" * 60)

    print(f"\n  sys.breakpointhook: {sys.breakpointhook}")
    print(f"  sys.__breakpointhook__: {sys.__breakpointhook__}")


if __name__ == "__main__":
    main()
