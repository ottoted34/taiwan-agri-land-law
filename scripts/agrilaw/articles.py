"""Article-number handling: '第 8-1 條', '第八條之一', '第29-1條' -> '8-1'."""
from __future__ import annotations

import re

from .util import cn_to_int, nfkc

_N = r"[0-9０-９一二三四五六七八九十百零〇]+"
_ART_RE = re.compile(rf"第\s*({_N})\s*(?:[-－]\s*({_N}))?\s*條(?:\s*之\s*({_N}))?")


def article_key(label: str) -> str | None:
    m = _ART_RE.search(nfkc(label))
    if not m:
        return None
    main = cn_to_int(m.group(1))
    if main is None:
        return None
    subtxt = m.group(2) or m.group(3)
    if subtxt:
        sub = cn_to_int(subtxt)
        return f"{main}-{sub}" if sub is not None else str(main)
    return str(main)


def article_label(key: str) -> str:
    if "-" in key:
        a, b = key.split("-", 1)
        return f"第 {a}-{b} 條"
    return f"第 {key} 條"


def sort_key(key: str) -> tuple[int, int]:
    a, _, b = key.partition("-")
    try:
        return int(a), int(b or 0)
    except ValueError:
        return 99999, 0


def split_fulltext_articles(text: str) -> list[dict]:
    """Split historical full text ('第一條\n...\n第二條\n...') into articles; chapter lines kept."""
    arts: list[dict] = []
    chapter = None
    cur = None
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            if cur:
                cur["text"] += "\n"
            continue
        if re.fullmatch(r"第\s*[一二三四五六七八九十百0-9]+\s*[章節編]\s*.*", s) and len(s) < 40:
            chapter = s
            continue
        m = re.fullmatch(r"(第\s*[0-9一二三四五六七八九十百零〇]+\s*條(?:之\s*[一二三四五六七八九十0-9]+)?)\s*(.*)", s)
        if m and article_key(m.group(1)):
            cur = {"key": article_key(m.group(1)), "chapter": chapter, "text": m.group(2).strip()}
            arts.append(cur)
            continue
        if cur:
            cur["text"] += ("\n" if cur["text"] and not cur["text"].endswith("\n") else "") + s
    for a in arts:
        a["text"] = re.sub(r"\n{2,}", "\n", a["text"]).strip()
        a["label"] = article_label(a["key"])
    return arts
