from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
DATA = ROOT / "data"
LAWS = DATA / "laws"
INTERP = DATA / "interpretations"
TECH = DATA / "technical"
RELATIONS = DATA / "relations"
META = DATA / "metadata"
UPDATES = DATA / "updates"
QUARANTINE = DATA / "quarantine"
WEB_DATA = ROOT / "web" / "public" / "data"
