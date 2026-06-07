"""async/await 底层实现探针。

演示内容：
  - 协程对象的创建
  - await 字节码
  - 协程的状态
"""

import asyncio
import dis


async def simple_coro():
    return 42


async def awaiting_coro():
    result = await simple_coro()
    return result


def main() -> None:
    print("=" * 60)
    print("async/await 探针")
    print("=" * 60)

    # ── 1. 协程对象的创建 ────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 协程对象")
    print("=" * 60)

    coro = simple_coro()
    print(f"  类型: {type(coro)}")
    print(f"  名称: {coro.__name__}")

    # ── 2. await 的字节码 ────────────────────────────────
    print("\n" + "=" * 60)
    print("2. await 字节码")
    print("=" * 60)

    print("  simple_coro:")
    dis.dis(simple_coro)
    print("\n  awaiting_coro:")
    dis.dis(awaiting_coro)

    # ── 3. 协程的执行 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 协程的执行")
    print("=" * 60)

    result = asyncio.run(simple_coro())
    print(f"  asyncio.run(simple_coro()) = {result}")


if __name__ == "__main__":
    main()
