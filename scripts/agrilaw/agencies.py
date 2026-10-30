"""Agency resolution, incl. pre-2023-08-01 COA agencies -> current successor (business only)."""
from __future__ import annotations

from functools import lru_cache

from .paths import CONFIG
from .util import load_yaml, nfkc


@lru_cache
def registry() -> dict:
    ag = load_yaml(CONFIG / "agencies" / "agencies.yaml")["agencies"]
    hist = load_yaml(CONFIG / "agencies" / "historical.yaml")
    return {"agencies": {a["id"]: a for a in ag}, "historical": hist}


def resolve(agency_text: str, date_iso: str | None, docno: str = "") -> dict:
    """Return {'agency_id', 'agency_name', 'historical_name', 'is_historical'}.
    Matching is textual; unknown agencies are kept verbatim with agency_id None."""
    reg = registry()
    t = nfkc(agency_text)
    reorg = reg["historical"]["reorg_date"]
    # longest historical name first
    for m in sorted(reg["historical"]["mappings"], key=lambda x: -len(x["historical"])):
        names = [m["historical"], *m.get("aliases", [])]
        if any(n and n in t for n in names) and "農業部" not in t:
            succ = reg["agencies"].get(m["successor"], {})
            return {"agency_id": m["successor"], "agency_name": succ.get("name"), "historical_name": m["historical"],
                    "is_historical": True}
    for a in sorted(reg["agencies"].values(), key=lambda x: -len(x["name"])):
        if a["name"] in t or (a.get("short") and a["short"] in t):
            return {"agency_id": a["id"], "agency_name": a["name"], "historical_name": None, "is_historical": False}
    if t in ("農業部",):
        return {"agency_id": "moa", "agency_name": "農業部", "historical_name": None, "is_historical": False}
    # no explicit agency text: before the reorganisation the issuer was the COA system
    if not t and date_iso and date_iso < reorg:
        return {"agency_id": None, "agency_name": None, "historical_name": "（原文未載發文機關；改制前文件）", "is_historical": True}
    return {"agency_id": None, "agency_name": t or None, "historical_name": None, "is_historical": bool(date_iso and date_iso < reorg)}
