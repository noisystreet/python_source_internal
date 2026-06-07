"""弱引用探针 —— 观察弱引用的行为与内部机制。

演示内容：
  - weakref.ref 基础：不增加引用计数，自动失效
  - 弱引用回调函数
  - WeakValueDictionary / WeakKeyDictionary / WeakSet
  - 哪些类型支持弱引用
  - 用弱引用打破循环引用
"""

import gc
import weakref


class BigObject:
    """一个用于测试的大对象。"""

    def __init__(self, name: str = ""):
        self.name = name

    def __repr__(self):
        return f"<BigObject '{self.name}' at {id(self):#x}>"


def main() -> None:
    print("=" * 60)
    print("弱引用探针")
    print("=" * 60)

    # ── 1. 弱引用基础 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 弱引用基础")
    print("=" * 60)

    obj = BigObject("test")
    ref = weakref.ref(obj)

    print(f"\nobj:               {obj}")
    print(f"ref:               {ref}")
    print(f"ref() 获取对象:     {ref()}")

    del obj
    print(f"del obj 后 ref():  {ref()}")  # None

    # ── 2. 回调函数 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("2. 弱引用回调")
    print("=" * 60)

    def on_death(ref):
        print(f"  回调触发: {ref} 指向的对象已被回收！")

    obj2 = BigObject("callback-test")
    ref2 = weakref.ref(obj2, on_death)

    print("  删除强引用前...")
    print(f"  ref2() = {ref2()}")
    del obj2
    print("  已删除强引用，回调应该在上方触发了")

    # ── 3. WeakValueDictionary ─────────────────────────────
    print("\n" + "=" * 60)
    print("3. WeakValueDictionary")
    print("=" * 60)

    wvd = weakref.WeakValueDictionary()
    obj3 = BigObject("wvd-test")

    wvd["key"] = obj3
    print(f"\n  字典中: {wvd.get('key')}")

    del obj3
    print(f"  删除后: {wvd.get('key')}")  # None

    # ── 4. WeakSet ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("4. WeakSet")
    print("=" * 60)

    ws = weakref.WeakSet()
    a = BigObject("a")
    b = BigObject("b")

    ws.add(a)
    ws.add(b)
    print(f"\n  WeakSet 中元素数: {len(ws)}")

    del a
    print(f"  删除 a 后元素数:   {len(ws)}")

    # ── 5. 哪些类型支持弱引用 ──────────────────────────────
    print("\n" + "=" * 60)
    print("5. 类型支持检测")
    print("=" * 60)

    class MyClass:
        pass

    test_objects = [
        ("MyClass 实例", MyClass()),
        ("list", [1, 2, 3]),
        ("dict", {"a": 1}),
        ("tuple", (1, 2)),
        ("set", {1, 2, 3}),
        ("int", 42),
        ("str", "hello"),
        ("function", lambda x: x),
        ("generator", (i for i in range(3))),
    ]

    for name, obj in test_objects:
        try:
            ref = weakref.ref(obj)
            print(f"  {name:>15}: OK")
        except TypeError:
            print(f"  {name:>15}: ❌ 不支持")
        finally:
            # 清理避免影响 gc
            del obj

    # ── 6. 弱引用打破循环引用 ──────────────────────────────
    print("\n" + "=" * 60)
    print("6. 弱引用打破循环引用")
    print("=" * 60)

    class Node:
        def __init__(self, name: str):
            self.name = name
            self.parent = None
            self.children = []  # 用强引用

    class WeakNode:
        """使用弱引用避免循环。"""
        def __init__(self, name: str):
            self.name = name
            self.parent = None
            self.children = []

        def add_child(self, child):
            self.children.append(child)
            # 用弱引用指向父节点，不形成强循环
            child._parent_ref = weakref.ref(self)

        @property
        def parent(self):
            if hasattr(self, '_parent_ref'):
                return self._parent_ref()
            return None

        @parent.setter
        def parent(self, value):
            if value is not None:
                self._parent_ref = weakref.ref(value)

    print("\n--- 循环引用问题 (Node 使用强引用) ---")
    parent = Node("parent")
    child = Node("child")
    parent.children.append(child)
    child.parent = parent

    # 删除外部引用，但因为有循环，对象不会被引用计数回收
    print("  创建循环 parent -> child -> parent")
    print(f"  gc.collect() 可以回收: {gc.collect()} 个")

    print("\n--- 使用 WeakNode (弱引用打破循环) ---")
    wp = WeakNode("weak-parent")
    wc = WeakNode("weak-child")
    wp.children.append(wc)
    wc.parent = wp  # 弱引用

    print("  parent 引用 child (强), child 引用 parent (弱)")
    print(f"  没有形成强循环，gc.collect() = {gc.collect()}")

    # ── 7. proxy 用法 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("7. weakref.proxy")
    print("=" * 60)

    obj7 = BigObject("proxy")
    proxy = weakref.proxy(obj7)

    print(f"\n  proxy.__class__:  {proxy.__class__}")
    print(f"  proxy.name:       {proxy.name}")
    print(f"  repr(proxy):      {repr(proxy)}")

    del obj7
    try:
        _ = proxy.name  # noqa: F841
    except ReferenceError as e:
        print(f"  删除后访问抛 ReferenceError: {e}")


if __name__ == "__main__":
    main()
