from pathlib import Path
import sys

from factory.process import normalize_command, resolve_executable


def test_python_is_resolved_to_current_interpreter():
    resolved = normalize_command("python -c \"print(1)\"")
    assert str(Path(sys.executable)) in resolved


def test_unknown_command_is_left_alone():
    assert normalize_command("echo hello") == "echo hello"


def test_resolver_returns_existing_python():
    python = resolve_executable("python")
    assert python is not None
    assert python.exists()
