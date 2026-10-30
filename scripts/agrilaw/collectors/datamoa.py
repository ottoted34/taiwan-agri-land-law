"""農業資料開放平臺 (data.moa.gov.tw) — 政府資料開放授權; JSON via DataFileService.
Used for publication catalogues of the research institutes / district agricultural
research & extension stations. We store bibliographic metadata + official links only;
PDF full text is NOT mirrored (publication copyright is not covered by the open-data licence)."""
from __future__ import annotations

import json
import re

from ..http import SourceError
from ..util import clean, load_yaml, nfkc, now_iso, sha256
from ..paths import CONFIG
from .base import CollectResult, Collector

SVC = "https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId={}"

# field aliases across datasets
TITLE = ["題目", "標題", "書名", "名稱", "主題", "篇名", "Title"]
DATE = ["出版日期年月", "出刊時間", "出版日期", "發布日期", "日期", "出版年月"]
LINK = ["連結位址1PDF", "檔案連結", "連結", "網址", "連結位址", "URL", "PDF連結"]
AUTHOR = ["作者", "撰稿人"]
ISSUE = ["編號", "期別", "期數", "卷期"]


def _first(rec: dict, keys: list[str]):
    for k in keys:
        if k in rec and rec[k] not in (None, ""):
            return rec[k]
    return None


def _ym(s) -> str | None:
    """'11508' (ROC yyy mm) / '202606' / '2026-06' -> '2026-08'."""
    if s is None:
        return None
    t = re.sub(r"\D", "", str(s))
    if len(t) == 6 and t.startswith(("19", "20")):
        return f"{t[:4]}-{t[4:6]}"
    if len(t) in (4, 5):
        y, m = int(t[:-2]), int(t[-2:])
        if 1 <= m <= 12:
            return f"{y + 1911}-{m:02d}"
    if len(t) == 8 and t.startswith(("19", "20")):
        return f"{t[:4]}-{t[4:6]}-{t[6:]}"
    return None


LIST_API = "https://data.moa.gov.tw/api/open_list.ashx"
PUB_TITLE = re.compile(r"專刊|彙報|專訊|月刊|季刊|期刊|出版|叢書|專輯|手冊|技術|農情|研究|成果|問答")
EXCLUDE_TITLE = re.compile(r"技術移轉|技轉|商標|品種權|專利|授權|徵才|採購|預算|決算")


def discover(client, agencies: dict) -> tuple[list[dict], list[str]]:
    """Find publication datasets of research institutes / stations in the MOA open-data catalogue."""
    found, notes, seen = [], [], set()
    names = {a["id"]: a for a in agencies.values() if a.get("priority", 3) <= 2}
    for aid, a in names.items():
        kw = a.get("short") or a["name"]
        for page in range(1, 4):
            try:
                r = client.s.post(LIST_API, data={"Page": page, "Limit": 50, "Keyword": kw, "Ord": 1,
                                                  "Sel_Catalog": "", "Sel_Organ": "", "Sel_Format": ""}, timeout=60)
                client.requests_made += 1
                payload = r.json()
            except Exception as e:  # noqa: BLE001
                notes.append(f"目錄查詢失敗 {kw}: {type(e).__name__}")
                break
            data = payload.get("Data") or []
            for it in data:
                title, organ = nfkc(it.get("Title")), nfkc(it.get("Organ"))
                short = a.get("short") or ""
                if it["ID"] in seen or not (short and (short in title or short in organ or short[:2] in organ)):
                    continue
                if PUB_TITLE.search(title) and not EXCLUDE_TITLE.search(title):
                    seen.add(it["ID"])
                    found.append({"unit_id": it["ID"], "title": title, "organ": organ, "agency_id": aid,
                                  "series": re.sub(r"^(.*?(改良場|試驗所|繁殖場|中心))", "", title) or title})
            if page >= int(payload.get("Total_pages") or 1):
                break
    return found, notes


class DataMoaPublications(Collector):
    source_id = "datamoa-publications"
    kind = "technical"

    def collect(self, mode: str) -> CollectResult:
        from ..agencies import registry
        from ..paths import META
        from ..util import read_json, write_json
        res = CollectResult(self.source_id, self.kind)
        static = load_yaml(CONFIG / "sources" / "technical_datasets.yaml")["datasets"]
        cat_path = META / "datamoa-catalog.json"
        catalog = read_json(cat_path, None)
        if mode in ("monthly", "full") or catalog is None:
            disc, notes = discover(self.client, registry()["agencies"])
            res.notes.extend(notes)
            if disc:
                catalog = {"discovered_at": now_iso(), "datasets": disc}
                write_json(cat_path, catalog)
            elif catalog is None:
                catalog = {"datasets": []}
        by_id = {d["unit_id"]: d for d in (catalog or {}).get("datasets", [])}
        for d in static:
            by_id[d["unit_id"]] = {**by_id.get(d["unit_id"], {}), **d}
        excluded = {str(x) for x in load_yaml(CONFIG / "sources" / "technical_datasets.yaml").get("exclude", [])}
        sets = [d for k, d in by_id.items() if k not in excluded]
        res.notes.append(f"出版品資料集 {len(sets)} 個")
        for ds in sets:
            url = SVC.format(ds["unit_id"])
            try:
                r = self.client.get(url, timeout=90)
                data = json.loads(r.content.decode("utf-8-sig"))
            except (SourceError, ValueError) as e:
                res.errors.append(f"{ds['unit_id']} {ds['title']}: {e}")
                continue
            if not isinstance(data, list):
                res.errors.append(f"{ds['unit_id']}: 非預期格式")
                continue
            n = 0
            for row in data:
                title = clean(str(_first(row, TITLE) or ""))
                issue = nfkc(str(_first(row, ISSUE) or ""))
                link = _first(row, LINK)
                if not title:
                    title = f"{ds['series']} {issue}".strip()
                if not title:
                    continue
                key = sha256([ds["unit_id"], issue, title])[:16]
                res.records.append({
                    "source_key": f"datamoa:{ds['unit_id']}:{key}",
                    "title": title,
                    "series": ds["series"],
                    "issue": issue,
                    "agency_id": ds["agency_id"],
                    "authors": clean(str(_first(row, AUTHOR) or "")),
                    "date": _ym(_first(row, DATE)),
                    "url": link,
                    "isbn": row.get("ISBN"),
                    "gpn": row.get("政府出版品編號GPN"),
                    "pages": row.get("頁數"),
                    "doc_class": "technical",
                    "license": "政府資料開放授權條款（書目資料）；出版品全文著作權依原發布機關",
                    "dataset": {"unit_id": ds["unit_id"], "title": ds["title"], "url": url},
                    "source": {"source_id": self.source_id, "url": url, "fetched_at": now_iso()},
                    "raw": {k: v for k, v in row.items() if v not in (None, "")},
                })
                n += 1
            res.notes.append(f"{ds['title']}：{n} 筆")
        res.requests = self.client.requests_made
        if res.errors:
            res.status = "partial" if res.records else "failed"
        return res
