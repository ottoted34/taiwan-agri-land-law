"""Shared helpers: dates (民國/西元), document numbers, hashing, JSON IO."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

TW = timezone(timedelta(hours=8))
FW_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
CN_NUM = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def now_iso() -> str:
    return datetime.now(TW).isoformat(timespec="seconds")


def nfkc(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[ \t　\xa0]+", " ", s).strip()


def cn_to_int(s: str) -> int | None:
    """Convert Chinese numerals up to 9999 (e.g. 一百零五, 二十九) or arabic digits."""
    s = s.strip().translate(FW_DIGITS)
    if s.isdigit():
        return int(s)
    total, section, num = 0, 0, 0
    units = {"十": 10, "百": 100, "千": 1000}
    if not s or any(ch not in CN_NUM and ch not in units for ch in s):
        return None
    for ch in s:
        if ch in CN_NUM:
            num = CN_NUM[ch]
        else:
            u = units[ch]
            section += (num or 1) * u
            num = 0
    return total + section + num


_ROC_PATTERNS = [
    re.compile(r"(?:民國)?\s*(\d{2,3})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})\s*日?"),
]


def roc_to_iso(text: str | None) -> str | None:
    """'115/7/28', '民國115年7月28日', '1150728', '2026-07-28' -> '2026-07-28'."""
    if not text:
        return None
    t = nfkc(text).translate(FW_DIGITS)
    m = re.search(r"(19|20)\d{2}-\d{1,2}-\d{1,2}", t)
    if m:
        y, mo, d = (int(x) for x in m.group(0).split("-"))
        return _safe(y, mo, d)
    m = re.search(r"\b(19|20)(\d{2})(\d{2})(\d{2})\b", t)
    if m:
        return _safe(int(m.group(1) + m.group(2)), int(m.group(3)), int(m.group(4)))
    m = re.search(r"(?<!\d)(\d{2,3})(\d{2})(\d{2})(?!\d)", t)
    if m and len(m.group(0)) == 7:
        return _safe(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3)))
    for p in _ROC_PATTERNS:
        m = p.search(t)
        if m:
            y = int(m.group(1))
            y = y + 1911 if y < 1000 else y
            return _safe(y, int(m.group(2)), int(m.group(3)))
    return None


def _safe(y: int, m: int, d: int) -> str | None:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def iso_to_roc(iso: str | None) -> str:
    if not iso:
        return ""
    y, m, d = (int(x) for x in iso[:10].split("-"))
    return f"民國{y - 1911}年{m}月{d}日"


DOCNO_RE = re.compile(r"([一-鿿]{1,8}字)\s*第\s*([0-9A-Za-z\-]+)\s*號")


def normalize_docno(s: str | None) -> str:
    """Canonical 發文字號: NFKC, remove spaces, upper-case letters. '農保規字第 1150230515 號' -> '農保規字第1150230515號'."""
    t = nfkc(s).translate(FW_DIGITS).replace(" ", "")
    m = DOCNO_RE.search(t)
    if not m:
        return t
    return f"{m.group(1)}第{m.group(2).upper()}號"


def docno_parts(s: str) -> tuple[str, str] | None:
    m = DOCNO_RE.search(normalize_docno(s))
    return (m.group(1), m.group(2)) if m else None


def find_docnos(text: str) -> list[str]:
    t = nfkc(text).translate(FW_DIGITS).replace(" ", "")
    return list(dict.fromkeys(f"{m.group(1)}第{m.group(2).upper()}號" for m in DOCNO_RE.finditer(t)))


def sha256(obj: Any) -> str:
    if not isinstance(obj, (bytes, str)):
        obj = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    if isinstance(obj, str):
        obj = obj.encode("utf-8")
    return hashlib.sha256(obj).hexdigest()


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write_json(path: Path, data: Any, compact: bool = False) -> None:
    """Atomic write: never leaves a half-written file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        if compact:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
        else:
            json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=False)
            f.write("\n")
    os.replace(tmp, path)


def load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def slug(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z一-鿿]+", "-", nfkc(s)).strip("-")
