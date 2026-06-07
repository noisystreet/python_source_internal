"""追踪探针 — 观察 sys.settrace 如何工作。

演示内容：
  - settrace 事件（call/return/line/exception）
  - 追踪函数的调用模式
"""

import sys


def trace_calls(frame, event, arg):
    """追踪函数调用事件。"""
    code = frame.f_code
    func_name = code.co_name
    if event in ('call', 'return'):
        print(f"  [{event:>8}] {func_name}")
    return trace_calls


def trace_lines(frame, event, arg):
    """追踪行事件。"""
    if event == 'line':
        print(f"  [line] {frame.f_code.co_name}:{frame.f_lineno}")
    return trace_lines


def traced_function():
    x = 1
    y = 2
    return x + y


def main() -> None:
    print("=" * 60)
    print("sys.settrace 探针")
    print("=" * 60)

    print("\n--- 函数调用追踪 (call/return) ---")
    sys.settrace(trace_calls)
    traced_function()
    sys.settrace(None)

    print("\n--- 行追踪 (line) ---")
    sys.settrace(trace_lines)
    traced_function()
    sys.settrace(None)


if __name__ == "__main__":
    main()
