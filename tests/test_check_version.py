import pytest
import tianze
from tools import check_version


@pytest.mark.parametrize("installed,tag,expected", [
    (tianze.__version__, None, 0),
    (tianze.__version__, f"v{tianze.__version__}", 0),
    (tianze.__version__, "v0.0.0", 1),
    ("0.0.0", None, 1),
])
def test_version_sources(monkeypatch, installed, tag, expected):
    monkeypatch.setattr(check_version.importlib.metadata, "version", lambda name: installed)
    monkeypatch.setenv("GITHUB_REF_TYPE", "tag" if tag else "branch")
    monkeypatch.setenv("GITHUB_REF_NAME", tag or "main")
    assert check_version.main() == expected
