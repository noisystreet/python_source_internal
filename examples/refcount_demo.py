"""引用计数演示 —— 观察对象引用计数的实时变化。

演示内容：
  - 赋值、传参对引用计数的影响
  - 容器（list、dict）对元素的引用
  - Immortal 对象的引用计数特征
  - 循环引用问题
"""

import gc
import sys


def show_refcount(label: str, obj, extra: str = "") -> None:
    """打印对象的引用计数和 id。"""
    rc = sys.getrefcount(obj) - 1  # 减去 getrefcount 自身的临时引用
    print(f"  {label:>20}: refcount={rc:>4}  id={id(obj):#x}  {extra}")


def main() -> None:
    print("=" * 60)
    print("引用计数探针")
    print("=" * 60)

    # ── 1. 基础引用计数变化 ──────────────────────────────────
    print("\n--- 1. 基础引用计数变化 ---")

    a = []
    show_refcount("a = []", a)

    b = a
    show_refcount("b = a 之后", a)

    lst = [a]
    show_refcount("lst = [a] 之后", a)

    d = {"key": a}
    show_refcount("d = {'key': a} 之后", a)

    del b
    show_refcount("del b 之后", a)

    lst.clear()
    show_refcount("lst.clear() 之后", a)

    del d["key"]
    show_refcount("del d['key'] 之后", a)

    # ── 2. Immortal 对象的引用计数 ──────────────────────────
    print("\n--- 2. Immortal 对象 ---")

    show_refcount("None", None)
    show_refcount("True", True)
    show_refcount("42 (小整数)", 42)
    show_refcount("257 (小整数边界)", 257)
    show_refcount("258 (普通整数)", 258)

    print("  immortal 对象的引用计数极大，但不意味着它被引用了那么多次。")
    print("  Py_INCREF/Py_DECREF 对它们都是空操作。")

    # ── 3. 函数调用的临时引用 ──────────────────────────────
    print("\n--- 3. 函数调用产生的临时引用 ---")

    def inspect(obj):
        # 函数内部：obj 是参数引用，调用 getrefcount 又产生一次临时引用
        rc_inner = sys.getrefcount(obj) - 1
        print(f"  函数内部: refcount = {rc_inner}")
        return rc_inner

    x = []
    rc_before = sys.getrefcount(x) - 1
    print(f"  调用前:   refcount = {rc_before}")
    _ = inspect(x)
    rc_after = sys.getrefcount(x) - 1
    print(f"  调用后:   refcount = {rc_after}")

    # ── 4. 循环引用 ──────────────────────────────────────────
    print("\n--- 4. 循环引用 ---")

    class Node:
        def __init__(self, name: str):
            self.name = name
            self.next = None

        def __del__(self):
            # 注意：循环引用下 __del__ 不会被引用计数触发
            pass

    a = Node("A")
    b = Node("B")
    a.next = b
    b.next = a

    print("  创建循环引用: A <-> B")
    show_refcount("a", a)
    show_refcount("b", b)

    del a
    del b
    print("  执行 del a, del b 后，对象仍然存活（循环引用）")
    print(f"  gc.collect() 可以回收: {gc.collect()} 个对象")

    # ── 5. sys.getrefcount 的特殊性 ──────────────────────────
    print("\n--- 5. getrefcount 的特殊性 ---")

    obj = object()
    raw_rc = sys.getrefcount(obj) - 1
    print(f"  sys.getrefcount(obj) - 1 = {raw_rc}")
    print("  (实际是 1，因为 obj 变量本身有一个引用)")

    # ── 6. 容器嵌套的引用链 ──────────────────────────────────
    print("\n--- 6. 容器嵌套引用链 ---")

    inner = []
    outer = [inner]
    show_refcount("inner (outer=[inner])", inner)

    outer2 = [inner]  # noqa: F841
    show_refcount("inner (outer2=[inner])", inner)

    outer.append(inner)
    show_refcount("inner (outer 2次)", inner)

    print("  一个对象可以被任意多个容器引用！")


if __name__ == "__main__":
    main()
