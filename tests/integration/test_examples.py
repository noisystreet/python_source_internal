"""示例脚本冒烟测试 — 逐个运行 examples/*.py 并验证退出码为 0。

每个脚本作为一个独立的 pytest 测试用例，便于定位失败脚本。
使用 subprocess 而非 import，避免副作用和 ctypes 地址冲突。
"""

import subprocess
import sys
import pytest
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples"

# 需要超时设置较长的脚本（秒）
SLOW_SCRIPTS = {
    "gil_demo.py": 120,       # 2 个线程各 1M 次循环
    "obmalloc_demo.py": 60,   # 大量对象分配
    "jit_demo.py": 60,        # 多次定时循环
    "tier2_demo.py": 60,      # 多次定时循环
    "ceval_loop_demo.py": 30,
    "list_demo.py": 30,
    "tuple_set_demo.py": 30,
    "unicode_demo.py": 30,
    "bytecodes_demo.py": 30,
    "longobject_demo.py": 30,
}


def collect_examples() -> list[Path]:
    """收集所有可运行的示例脚本。"""
    scripts = sorted(EXAMPLES_DIR.glob("*.py"))
    return [s for s in scripts if s.name != "__init__.py"]


def run_script(script: Path) -> dict:
    """运行一个示例脚本，返回结果。"""
    timeout = SLOW_SCRIPTS.get(script.name, 20)
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "name": script.name,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "name": script.name,
            "returncode": -1,
            "stdout": "",
            "stderr": f"TIMEOUT after {timeout}s",
        }


# pytest 参数化：每个脚本生成一个独立测试用例
_example_scripts = collect_examples()


@pytest.mark.parametrize(
    "script",
    [pytest.param(s, id=s.name) for s in _example_scripts],
)
def test_example_script(script: Path):
    """运行单个示例脚本，验证退出码为 0。"""
    result = run_script(script)
    assert result["returncode"] == 0, (
        f"\n  exit code: {result['returncode']}"
        f"\n  stderr: {result['stderr'][:2000]}"
        f"\n  stdout (last 500): {result['stdout'][-500:]}"
    )
