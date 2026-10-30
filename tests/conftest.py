import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
FIX = ROOT / "tests" / "fixtures"


@pytest.fixture
def fixtures():
    return FIX


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Point every data path at an empty temp folder; config stays real."""
    from agrilaw import paths
    d = tmp_path / "data"
    for name, sub in [("DATA", ""), ("LAWS", "laws"), ("INTERP", "interpretations"), ("TECH", "technical"),
                      ("RELATIONS", "relations"), ("META", "metadata"), ("UPDATES", "updates"), ("QUARANTINE", "quarantine")]:
        monkeypatch.setattr(paths, name, d / sub if sub else d)
    monkeypatch.setattr(paths, "WEB_DATA", tmp_path / "web-data")
    import agrilaw.collectors.rmis as rmis_mod
    monkeypatch.setattr(rmis_mod.time, "sleep", lambda s: None)  # retries must not slow tests
    return d
