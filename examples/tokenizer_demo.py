"""Tokenizer 探针 — 观察 Python 源码如何被切分为 token。

演示内容：
  - 使用 tokenize 模块展示 token 流
  - 关键字识别
  - 缩进 INDENT/DEDENT
  - 字符串和数字
  - f-string
"""

import io
import keyword
import tokenize


def tokenize_source(source: str) -> list:
    """对一段源码进行词法分析，返回 token 列表。"""
    tokens = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            tokens.append(tok)
    except tokenize.TokenError as e:
        print(f"  Tokenize error: {e}")
    return tokens


def print_tokens(tokens: list) -> None:
    """打印 token 列表。"""
    for tok in tokens:
        type_name = tokenize.tok_name[tok.type]
        line = tok.start[0]
        start = f"({tok.start[0]},{tok.start[1]})"
        end = f"({tok.end[0]},{tok.end[1]})"
        if tok.type == tokenize.ENDMARKER:
            print(f"  行 {line}: {type_name}")
        elif tok.type == tokenize.NEWLINE:
            print(f"  行 {line}: {type_name}")
        elif tok.type == tokenize.INDENT:
            print(f"  行 {line}: {type_name}")
        elif tok.type == tokenize.DEDENT:
            print(f"  行 {line}: {type_name}")
        else:
            value = tok.string
            print(f"  行 {line}: {type_name:>8} '{value}' {start}-{end}")


def main() -> None:
    print("=" * 60)
    print("Tokenizer 词法分析探针")
    print("=" * 60)

    # ── 1. 简单表达式 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 简单表达式 token 流")
    print("=" * 60)

    source1 = "x = 42 + (y - 1)"
    print(f"\n  源码: '{source1}'")
    tokens1 = tokenize_source(source1)
    print_tokens(tokens1)

    # ── 2. 关键字识别 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 关键字识别")
    print("=" * 60)

    for word in ["if", "for", "while", "class", "def", "return", "xyz", "hello"]:
        is_kw = keyword.iskeyword(word)
        print(f"  '{word}' → {'keyword' if is_kw else 'identifier'}")

    # ── 3. 缩进 INDENT/DEDENT ─────────────────────────────
    print("\n" + "=" * 60)
    print("3. 缩进处理")
    print("=" * 60)

    source2 = """def f():
    if x:
        pass
"""
    print(f"\n  源码:\n{source2}")
    tokens2 = tokenize_source(source2)
    print_tokens(tokens2)

    # ── 4. 各种 token 类型 ────────────────────────────────
    print("\n" + "=" * 60)
    print("4. 各种 token 类型")
    print("=" * 60)

    source3 = """42 3.14 "hello" b"bytes" True None [1, 2] {3, 4}"""
    tokens3 = tokenize_source(source3)
    print_tokens(tokens3)

    # ── 5. f-string ───────────────────────────────────────
    print("\n" + "=" * 60)
    print("5. f-string")
    print("=" * 60)

    source4 = 'f"hello {name.upper()!r} world"'
    print(f"\n  源码: {source4}")
    tokens4 = tokenize_source(source4)
    print_tokens(tokens4)

    # ── 6. 运算符 ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("6. 运算符 token")
    print("=" * 60)

    source5 = "a += b // c ** d @= e"
    tokens5 = tokenize_source(source5)
    print_tokens(tokens5)


if __name__ == "__main__":
    main()
