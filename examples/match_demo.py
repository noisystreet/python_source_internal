"""match/case 探针 — 观察模式匹配的字节码和行为。"""

import dis


def demo_match(value):
    match value:
        case 1:
            return "one"
        case str():
            return "a string"
        case _:
            return "something else"


def main() -> None:
    print("=" * 60)
    print("match/case 探针")
    print("=" * 60)

    print("\n1. 调用结果")
    print(f"   demo_match(1)      -> {demo_match(1)}")
    print(f"   demo_match('hi')   -> {demo_match('hi')}")
    print(f"   demo_match(3.14)   -> {demo_match(3.14)}")

    print("\n2. 字节码（MATCH_CLASS / MATCH_KEYS 等）")
    dis.dis(demo_match)


if __name__ == "__main__":
    main()
