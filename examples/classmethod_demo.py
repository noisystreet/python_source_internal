"""classmethod / staticmethod 探针。"""


class C:
    @classmethod
    def f(cls):
        return cls

    @staticmethod
    def g(x):
        return x

    def h(self):
        return self


def main() -> None:
    print("=" * 60)
    print("classmethod / staticmethod 探针")
    print("=" * 60)

    obj = C()

    # 1. 类型观察
    print("\n1. 类型")
    print(f"   C.__dict__['f'] type: {type(C.__dict__['f'])}")
    print(f"   C.__dict__['g'] type: {type(C.__dict__['g'])}")
    print(f"   C.__dict__['h'] type: {type(C.__dict__['h'])}")

    # 2. 调用
    print("\n2. 调用")
    print(f"   C.f() -> {C.f()}")
    print(f"   C.g(42) -> {C.g(42)}")

    # 3. 类方法通过实例调用
    print(f"\n3. obj.f() -> {obj.f()}")
    print(f"   obj.g(42) -> {obj.g(42)}")


if __name__ == "__main__":
    main()
