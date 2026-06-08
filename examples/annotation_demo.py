"""PEP 649 延迟注解探针 — 观察注解评估时机。"""

import sys


def f(x: int) -> str:
    ...


def g(x: "some.UnknownType") -> None:
    """3.13- 会报 NameError, 3.14+ 通过 PEP 649 正常."""
    ...


def main() -> None:
    print("=" * 60)
    print("PEP 649 延迟注解探针")
    print("=" * 60)

    print(f"\nPython 版本: {sys.version_info.major}.{sys.version_info.minor}")

    print("\n1. 注解是否立即评估？")
    print(f"   f.__annotations__: {f.__annotations__}")
    print(f"   g.__annotations__: {g.__annotations__}")
    print(f"   (3.14+ 的 g.__annotations__ 可能在首次访问时评估)")

    print("\n2. 注解类型")
    print(f"   f.__annotations__['return']: {f.__annotations__['return']}")


if __name__ == "__main__":
    main()
