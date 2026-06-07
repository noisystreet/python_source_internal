"""super() 探针 — 观察 MRO 与方法解析路径。"""



class A:
    def f(self): return "A"

class B(A):
    def f(self): return super().f() + "B"

class C(A):
    def f(self): return super().f() + "C"

class D(B, C):
    def f(self): return super().f() + "D"


def main() -> None:
    print("=" * 60)
    print("super() 探针")
    print("=" * 60)

    print("\n1. MRO")
    print(f"  D.mro() = {[c.__name__ for c in D.__mro__]}")

    print("\n2. super() 调用链")
    result = D().f()
    print(f"  D().f() = {result!r}")
    print("  调用链: D → B → super → C → super → A")

    print("\n3. super() 对象结构")
    class E:
        def test_super(self):
            s = super()
            print(f"  super object type: {type(s)}")
            print(f"  super.__thisclass__: {s.__thisclass__}")
            print(f"  super.__self__: {s.__self__}")
            print(f"  super.__self_class__: {s.__self_class__}")

    E().test_super()


if __name__ == "__main__":
    main()
