from pathlib import Path

from factory.daemon import ROJO_VERSION, FactoryLock


def test_rojo_version_is_pinned():
    assert ROJO_VERSION == "7.6.1"


def test_factory_lock_creates_lock_file(tmp_path: Path):
    lock = tmp_path / "factory.lock"
    with FactoryLock(lock):
        assert lock.exists()


def test_scheduler_is_hidden_and_non_overlapping():
    root = Path(__file__).resolve().parents[1]
    text = (root / "scripts/install-scheduler.ps1").read_text(encoding="utf-8")
    assert "-Hidden" in text
    assert "IgnoreNew" in text
    assert "pythonw.exe" in text
    assert "wscript.exe" in text
