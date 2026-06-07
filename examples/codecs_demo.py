"""Codec 系统探针。

演示内容：
  - 编码/解码
"""

import codecs


def main() -> None:
    print("=" * 60)
    print("Codec 系统探针")
    print("=" * 60)

    text = "你好，世界"
    encoded = text.encode("utf-8")
    decoded = encoded.decode("utf-8")
    print(f"  原文: {text}")
    print(f"  编码: {encoded}")
    print(f"  解码: {decoded}")

    lookup = codecs.lookup("utf-8")
    print(f"  codecs.lookup('utf-8'): {lookup.name}")


if __name__ == "__main__":
    main()
