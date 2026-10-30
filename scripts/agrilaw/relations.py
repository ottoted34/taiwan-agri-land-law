"""Relations between interpretations, laws and articles.
kind:
  official   - listed by the competent authority's own system (RMIS 法規對應解釋函)
  extracted  - algorithmic suggestion from the letter's text (law name + article number)
  manual     - human-confirmed entry in config/relations/manual.yaml (must cite evidence)
None of these alone decides legal applicability."""
from __future__ import annotations

import re

from .paths import CONFIG
from .util import cn_to_int, load_yaml, nfkc

ART = r"第\s*([0-9０-９一二三四五六七八九十百零〇]+)\s*條(?:\s*之\s*([0-9一二三四五六七八九十]+))?"


def law_name_map(laws: list[dict]) -> dict[str, str]:
    names = {l["name"]: l["id"] for l in laws}
    for alias, full in (load_yaml(CONFIG / "synonyms" / "law_aliases.yaml").get("aliases") or {}).items():
        if full in names:
            names[alias] = names[full]
    for l in laws:  # historical names, e.g. 農業用地容許作農業設施使用審查辦法
        for h in l.get("former_names", []):
            names.setdefault(h, l["id"])
    return names


def extract_refs(text: str, names: dict[str, str]) -> list[dict]:
    """Find '<law name>第X條(之Y)' (optionally in 「」) and bare law-name mentions."""
    t = nfkc(text)
    out: dict[tuple, dict] = {}
    alts = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    if not alts:
        return []
    for m in re.finditer(rf"[「『]?({alts})[」』]?(?:\s*(?:（[^）]{{0,20}}）)?\s*{ART})?", t):
        law_id = names[m.group(1)]
        art = None
        if m.group(2):
            main = cn_to_int(m.group(2))
            sub = cn_to_int(m.group(3)) if m.group(3) else None
            if main is not None:
                art = f"{main}-{sub}" if sub else str(main)
        key = (law_id, art)
        if key not in out:
            s = max(0, m.start() - 30)
            out[key] = {"law_id": law_id, "article": art, "snippet": t[s:m.end() + 40]}
    # drop law-level duplicates when article-level refs exist for same law
    with_art = {k[0] for k in out if k[1]}
    return [v for k, v in out.items() if k[1] or k[0] not in with_art]


def manual_entries() -> dict:
    return load_yaml(CONFIG / "relations" / "manual.yaml") or {}
