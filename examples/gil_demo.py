"""GIL 探针 — 观察 GIL 对多线程的影响。

演示内容：
  - GIL 下的计数竞争
  - GIL 切换
  - sys.setswitchinterval
"""

import sys
import threading


def main() -> None:
    print("=" * 60)
    print("GIL 探针")
    print("=" * 60)

    # ── 1. GIL 下的计数器竞争 ────────────────────────────
    print("\n" + "=" * 60)
    print("1. 计数器竞争演示")
    print("=" * 60)

    n = 1000000
    counter = 0

    def increment():
        nonlocal counter
        for _ in range(n):
            counter += 1

    t1 = threading.Thread(target=increment)
    t2 = threading.Thread(target=increment)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print(f"  预期: {n * 2}")
    print(f"  实际: {counter}")
    print("  GIL 保护了字节码级别，但 += 是三条字节码指令")

    # ── 2. 切换间隔 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. GIL 切换间隔")
    print("=" * 60)

    interval = sys.getswitchinterval()
    print(f"  当前切换间隔: {interval * 1000:.1f}ms")
    print("  GIL 默认每执行 5ms 的字节码就尝试切换线程")


if __name__ == "__main__":
    main()
