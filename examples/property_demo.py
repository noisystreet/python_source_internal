"""property 探针 — 观察 C 层描述符行为。"""


class C:
    @property
    def x(self):
        """The x property."""
        return 42

    @x.setter
    def x(self, value):
        self._x = value


def main() -> None:
    print("=" * 60)
    print("property 探针")
    print("=" * 60)

    obj = C()

    # 1. 读取
    print(f"\n1. obj.x = {obj.x}")

    # 2. 观察类型
    print(f"\n2. C.__dict__['x'] type: {type(C.__dict__['x'])}")
    print(f"   fget: {C.__dict__['x'].fget}")
    print(f"   fset: {C.__dict__['x'].fset}")

    # 3. 设置
    obj.x = 99
    print(f"\n3. obj.x = 99 后: obj._x = {obj._x}")


if __name__ == "__main__":
    main()
