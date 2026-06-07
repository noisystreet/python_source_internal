"""描述符探针 —— 观察描述符协议和 Python 属性访问机制。

演示内容：
  - 属性查找优先级链
  - property 描述符
  - 方法描述符（bound method）
  - 自定义描述符
  - staticmethod / classmethod
"""

import ctypes

# ── 自定义描述符示例 ─────────────────────────────────────

class PositiveNumber:
    """数据描述符：只允许正数。"""

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, 0)

    def __set__(self, obj, value):
        if value <= 0:
            raise ValueError(f"{self.name} must be positive")
        obj.__dict__[self.name] = value


class ReadOnly:
    """非数据描述符：只读属性（只有 __get__，没有 __set__）。"""

    def __init__(self, value):
        self.value = value

    def __get__(self, obj, objtype=None):
        return self.value


# ── 测试类 ──────────────────────────────────────────────

class Demo:
    x = 10              # 普通类属性
    y = property(lambda self: 42, doc="property 描述符")
    z = ReadOnly(100)   # 非数据描述符
    n = PositiveNumber()  # 数据描述符

    def method(self):
        return "method called"

    @staticmethod
    def static_method():
        return "static"

    @classmethod
    def class_method(cls):
        return f"classmethod of {cls.__name__}"


def method_type_name(obj) -> str:
    type_name = type(obj).__name__ if obj is not None else "None"
    return type_name


def main() -> None:
    print("=" * 60)
    print("描述符协议探针")
    print("=" * 60)

    # ── 1. 描述符优先级 ────────────────────────────────────
    print("\n" + "=" * 60)
    print("1. 描述符查找优先级")
    print("=" * 60)

    obj = Demo()

    # 普通类属性
    print(f"\n  Demo.x = {Demo.x} (类属性)")
    print(f"  obj.x = {obj.x} (通过实例访问类属性)")

    # property 描述符
    print(f"\n  Demo.y = {Demo.y} (property 对象本身)")
    print(f"  obj.y = {obj.y} (调用 property.__get__ → 42)")

    # 非数据描述符
    print(f"\n  Demo.z = {Demo.z} (ReadOnly 描述符)")
    print(f"  obj.z = {obj.z} (调用 ReadOnly.__get__ → 100)")

    # 验证优先级
    print("\n  --- 验证优先级 ---")
    obj.__dict__["z"] = 999
    print("  设置 obj.__dict__['z'] = 999 后")
    print(f"  obj.z = {obj.z}")
    print("  非数据描述符 → 实例 __dict__ 优先级更高")

    # 数据描述符覆盖实例字典
    obj.__dict__["n"] = -999
    print("\n  设置 obj.__dict__['n'] = -999 后")
    try:
        print(f"  obj.n = {obj.n}")
    except ValueError as e:
        print(f"  obj.n -> ValueError: {e}")
    print("  数据描述符 → 优先级高于实例 __dict__")

    # ── 2. property 描述符 ──────────────────────────────────
    print("\n" + "=" * 60)
    print("2. property 描述符")
    print("=" * 60)

    class Circle:
        def __init__(self, radius):
            self._radius = radius

        @property
        def radius(self):
            return self._radius

        @radius.setter
        def radius(self, value):
            if value <= 0:
                raise ValueError("Radius must be positive")
            self._radius = value

        @property
        def area(self):
            return 3.14159 * self._radius ** 2

    c = Circle(5)
    print(f"  c.radius = {c.radius}")
    print(f"  c.area = {c.area:.4f}")
    c.radius = 10
    print(f"  设置 radius=10 后: c.radius = {c.radius}")
    try:
        c.radius = -1
    except ValueError as e:
        print(f"  设置 radius=-1 -> ValueError: {e}")

    # ── 3. 方法描述符 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("3. 方法描述符")
    print("=" * 60)

    print(f"\n  Demo.method = {Demo.method}")
    print(f"  类型: {type(Demo.method).__name__}")

    bound = obj.method
    print(f"\n  obj.method = {bound}")
    print(f"  类型: {type(bound).__name__}")
    print(f"  调用: obj.method() = {bound()}")

    # ── 4. staticmethod / classmethod ─────────────────────
    print("\n" + "=" * 60)
    print("4. staticmethod / classmethod")
    print("=" * 60)

    print(f"\n  Demo.static_method = {Demo.static_method}")
    print(f"  obj.static_method() = {obj.static_method()}")

    print(f"\n  Demo.class_method = {Demo.class_method}")
    print(f"  obj.class_method() = {obj.class_method()}")

    # ── 5. 没有 __getattr__ vs 有 __getattr__ ──────────────
    print("\n" + "=" * 60)
    print("5. __getattr__ vs __getattribute__")
    print("=" * 60)

    class WithGetAttr:
        def __getattr__(self, name):
            return f"fallback: {name}"

    wa = WithGetAttr()
    print("\n  wa.existing_attr: 先正常查找")
    print(f"  wa.nonexistent: {wa.nonexistent} (__getattr__ 兜底)")

    # ── 6. 用 ctypes 查看方法对象 ──────────────────────────
    print("\n" + "=" * 60)
    print("6. 用 ctypes 查看 bound method 结构")
    print("=" * 60)

    bound_method = obj.method
    addr = id(bound_method)

    # PyMethodObject 字段 (64-bit):
    # PyObject_HEAD: 16B
    # m_self (PyObject*): +16, 8B
    # m_func (PyObject*): +24, 8B

    m_self = ctypes.c_void_p.from_address(addr + 16).value
    m_func = ctypes.c_void_p.from_address(addr + 24).value

    print(f"  bound method 地址: {hex(addr)}")
    print(f"  m_self (绑定的实例): {hex(m_self)}")
    print(f"  m_func (原始函数):   {hex(m_func)}")


if __name__ == "__main__":
    main()
