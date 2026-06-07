"""marshal 探针 — 观察 CPython 的序列化格式。

演示内容：
  - 序列化/反序列化
  - 代码对象的序列化
"""

import marshal


def main() -> None:
    print("=" * 60)
    print("marshal 探针")
    print("=" * 60)

    data = [1, 2, 3, "hello", {"a": 1}]
    serialized = marshal.dumps(data)
    deserialized = marshal.loads(serialized)
    print(f"  原始: {data}")
    print(f"  序列化: {serialized.hex()[:40]}... ({len(serialized)} 字节)")
    print(f"  反序列化: {deserialized}")

    # 代码对象
    def f():
        return 42

    code_bytes = marshal.dumps(f.__code__)
    print(f"\n  代码对象序列化: {len(code_bytes)} 字节")


if __name__ == "__main__":
    main()
