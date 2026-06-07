"""Traceback 探针 — 观察异常发生时的栈信息。

演示内容：
  - 异常发生时 traceback 的内容
  - 栈展开
  - sys.exc_info
"""

import traceback


def inner():
    return 1 / 0

def outer():
    return inner()

def main() -> None:
    print("=" * 60)
    print("Traceback 探针")
    print("=" * 60)

    print("\n--- 捕获并打印 traceback ---")
    try:
        outer()
    except ZeroDivisionError:
        print("  Traceback 对象:")
        traceback.print_exc()

    print("\n--- 格式化 traceback ---")
    try:
        outer()
    except ZeroDivisionError:
        lines = traceback.format_exc().strip().split('\n')
        for line in lines:
            print(f"  {line}")


if __name__ == "__main__":
    main()
