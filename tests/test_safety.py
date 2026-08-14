from pathlib import Path


def test_runner_does_not_publish_by_default():
    text = (Path(__file__).resolve().parents[1] / "src/factory/runner.py").read_text(encoding="utf-8")
    assert 'os.environ.get("AUTO_PUBLISH", "0") != "1"' in text
    assert '"Saved"' in text
    assert '"Published"' in text


def test_no_cookie_auth_or_secret_printing():
    root = Path(__file__).resolve().parents[1] / "src/factory"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert ".ROBLOSECURITY" not in text
    assert "print(self._api_key)" not in text
