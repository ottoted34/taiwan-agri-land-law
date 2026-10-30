"""全國法規資料庫 Open API（法務部）— official open data, full text of 法律 and 命令.
Endpoints return a zip with ChLaw.json / ChOrder.json. We keep only configured laws."""
from __future__ import annotations

import ast
import io
import json
import re
import zipfile

from ..articles import article_key, article_label
from ..http import SourceError
from ..util import load_yaml, nfkc, now_iso, roc_to_iso
from ..paths import CONFIG
from .base import CollectResult, Collector

ENDPOINTS = {"law": "https://law.moj.gov.tw/api/ch/law/json", "order": "https://law.moj.gov.tw/api/ch/order/json"}


def _attachments(v) -> list[dict]:
    if not v:
        return []
    if isinstance(v, str):
        try:
            v = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            try:
                v = json.loads(v)
            except ValueError:
                return []
    return [{"name": nfkc(a.get("FileName")), "url": a.get("FileURL")} for a in v if isinstance(a, dict)]


def _histories(text: str) -> list[dict]:
    """'1.中華民國...號令訂定...\r\n  ...' -> [{seq, text, date}]"""
    if not text:
        return []
    joined = re.sub(r"\r?\n\s*", "", text)
    parts = re.split(r"(?:(?<=^)|(?<=[。；行\)）]))\s*(\d{1,3})\.(?=中華民國|民國)", joined)
    out = []
    if len(parts) > 1:
        it = iter(parts[1:])
        for seq, body in zip(it, it):
            out.append({"seq": int(seq), "text": nfkc(body), "date": _roc_cn_date(body)})
    else:
        out.append({"seq": 1, "text": nfkc(joined), "date": _roc_cn_date(joined)})
    return out


_CN_YEAR = re.compile(r"中華民國([一二三四五六七八九十百零〇]+)年([一二三四五六七八九十]+)月([一二三四五六七八九十]+)日")


def _roc_cn_date(s: str) -> str | None:
    from ..util import cn_to_int
    m = _CN_YEAR.search(s)
    if not m:
        return roc_to_iso(s)
    y, mo, d = (cn_to_int(x) for x in m.groups())
    if None in (y, mo, d):
        return None
    return roc_to_iso(f"{y}/{mo}/{d}")


def normalize_law(raw: dict, level_hint: str) -> dict:
    pcode = None
    m = re.search(r"pcode=([A-Za-z0-9]+)", raw.get("LawURL") or "", re.I)
    if m:
        pcode = m.group(1).upper()
    articles, chapter = [], None
    for a in raw.get("LawArticles") or []:
        if a.get("ArticleType") == "C":
            chapter = nfkc(a.get("ArticleContent"))
            continue
        key = article_key(a.get("ArticleNo") or "")
        if not key:
            continue
        articles.append({"key": key, "label": article_label(key), "chapter": chapter,
                         "text": (a.get("ArticleContent") or "").replace("\r\n", "\n").strip()})
    abandon = nfkc(raw.get("LawAbandonNote"))
    eff_note = nfkc(raw.get("LawEffectiveNote"))
    status = "current"
    if abandon:
        status = "abolished"
    elif eff_note and re.search(r"尚未|另定|施行日期", eff_note):
        status = "partially_pending"
    return {
        "id": pcode,
        "name": nfkc(raw.get("LawName")),
        "level": nfkc(raw.get("LawLevel")) or level_hint,
        "category": nfkc(raw.get("LawCategory")),
        "official_url": f"https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={pcode}" if pcode else raw.get("LawURL"),
        "modified_date": roc_to_iso(raw.get("LawModifiedDate")) if raw.get("LawModifiedDate") else None,
        "effective_date": roc_to_iso(raw.get("LawEffectiveDate")) if raw.get("LawEffectiveDate") else None,
        "effective_note": eff_note,
        "abandon_note": abandon,
        "status": status,
        "histories": _histories(raw.get("LawHistories") or ""),
        "foreword": nfkc(raw.get("LawForeword")),
        "articles": articles,
        "attachments": _attachments(raw.get("LawAttachements")),
    }


class MojLawCollector(Collector):
    source_id = "moj-law-api"
    kind = "law"

    def targets(self) -> list[dict]:
        return load_yaml(CONFIG / "sources" / "laws.yaml")["laws"]

    def collect(self, mode: str) -> CollectResult:
        res = CollectResult(self.source_id, self.kind)
        want = {t["name"]: t for t in self.targets()}
        found: set[str] = set()
        update_dates = {}
        for level, url in ENDPOINTS.items():
            try:
                r = self.client.get(url, timeout=300)
                z = zipfile.ZipFile(io.BytesIO(r.content))
                name = next(n for n in z.namelist() if n.lower().endswith(".json"))
                data = json.loads(z.read(name).decode("utf-8-sig"))
            except (SourceError, zipfile.BadZipFile, StopIteration, ValueError) as e:
                res.errors.append(f"{url}: {e}")
                continue
            laws = data.get("Laws") or []
            if len(laws) < 100:  # whole national database cannot legitimately be this small
                res.errors.append(f"{url}: only {len(laws)} records, treated as malformed")
                continue
            update_dates[level] = data.get("UpdateDate")
            for raw in laws:
                nm = nfkc(raw.get("LawName"))
                if nm in want and nm not in found:
                    rec = normalize_law(raw, "法律" if level == "law" else "命令")
                    rec["topics"] = want[nm].get("topics", [])
                    rec["core"] = bool(want[nm].get("core"))
                    rec["source"] = {"source_id": self.source_id, "url": url, "dataset_update": data.get("UpdateDate"),
                                     "fetched_at": now_iso()}
                    res.records.append(rec)
                    found.add(nm)
        missing = sorted(set(want) - found)
        if missing:
            res.notes.append("全國法規資料庫查無（名稱不符或已廢止）：" + "、".join(missing))
        res.notes.append(f"資料集更新日期：{update_dates}")
        res.requests = self.client.requests_made
        if res.errors and not res.records:
            res.status = "failed"
        elif res.errors:
            res.status = "partial"
            res.complete = False
        return res
