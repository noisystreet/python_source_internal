"""异常处理链探针 — 观察 try/except/finally 的字节码和异常传播。

演示内容：
  - try/except/finally 的字节码
  - 异常传播路径
"""

import dis


def demo_basic():
    try:
        1 / 0
    except ZeroDivisionError:
        return "caught"
    finally:
        pass


def demo_propagation():
    def inner():
        1 / 0
    def outer():
        inner()
    try:
        outer()
    except ZeroDivisionError as e:
        return f"caught: {e}"


def main() -> None:
    print("=" * 60)
    print("异常处理链探针")
    print("=" * 60)

    print("\n--- try/except/finally 字节码 ---")
    dis.dis(demo_basic)

    print("\n--- 异常传播 ---")
    result = demo_propagation()
    print(f"  异常传播测试: {result}")


if __name__ == "__main__":
    main()
