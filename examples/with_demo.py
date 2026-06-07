"""with 语句探针 — 观察 BEFORE_WITH / __enter__ / __exit__ 行为。"""

import dis


def demo_with():
    with open("/dev/null") as f:
        return f.read()


def main() -> None:
    print("=" * 60)
    print("with 语句探针")
    print("=" * 60)

    print("\n1. with 的字节码（BEFORE_WITH）")
    dis.dis(demo_with)

    print("\n2. 自定义上下文管理器")
    class MyContext:
        def __enter__(self):
            print("   [__enter__ 被调用]")
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            print(f"   [__exit__ 被调用] type={exc_type}, val={exc_val}")
            return False

    with MyContext() as ctx:
        print(f"   ctx = {ctx}")

    print("\n3. __exit__ 抑制异常")
    class SuppressContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            print(f"   [抑制异常: {exc_type}]")
            return True  # 抑制异常

    with SuppressContext():
        raise ValueError("这个异常被抑制了")
    print("   (异常被 __exit__ 抑制，代码继续执行)")


if __name__ == "__main__":
    main()
