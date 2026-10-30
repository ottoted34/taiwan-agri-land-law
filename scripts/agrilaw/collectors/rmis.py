"""農業部農村發展及水土保持署「農地及農舍法規檢索系統」(RMIS).
Public pages, no robots.txt restrictions (checked at runtime on every run).
Three collectors share the parsers below:
  RmisInterpretations : 最新解釋函列表 (NewsList, full archive since 民國89) + NewsDetail full text
  RmisLaws            : 法規目錄 / 法規內容 / 歷史沿革 (incl. administrative rules not in MOJ)
  RmisLawExp          : 法規對應解釋函 (official law -> interpretation listing)"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..articles import article_key, article_label, split_fulltext_articles
from ..html import by_id_suffix, soup, text_of
from ..http import SourceError
from ..util import clean, nfkc, normalize_docno, now_iso, roc_to_iso, sha256
from .base import CollectResult, Collector

BASE = "https://rmis.ardswc.gov.tw/Web/"


# ---------------------------------------------------------------- parsers
def parse_news_list(html: str) -> tuple[list[dict], int | None]:
    doc = soup(html)
    rows = []
    for a in doc.find_all("a", id=re.compile(r"lvList_hlkEdit_\d+$")):
        idx = re.search(r"_(\d+)$", a["id"]).group(1)
        get = lambda k: nfkc(text_of(doc.find(id=re.compile(rf"lvList_{k}_{idx}$")), False))
        m = re.search(r"id=(\d+)", a.get("href", ""))
        if not m:
            continue
        rows.append({
            "rmis_id": int(m.group(1)),
            "date_text": get("lblExpDate"),
            "docno_text": get("lblExpWord"),
            "subject": clean(a.get_text()),
            "category": get("lblExpClass"),
        })
    last = None
    for href in [x.get("href", "") for x in doc.find_all("a")]:
        m = re.search(r"NewsList\.aspx\?page=(\d+)", href)
        if m:
            last = max(last or 0, int(m.group(1)))
    return rows, last


def parse_news_detail(html: str) -> dict | None:
    doc = soup(html)
    word = by_id_suffix(doc, "ucNewsDetailOut1_lblExpWord")
    if word is None:  # invalid ids redirect to the list page
        return None
    g = lambda k: text_of(by_id_suffix(doc, f"ucNewsDetailOut1_{k}"))
    serial = doc.find(id=re.compile(r"ucNewsDetailOut1_hfExpSn$"))
    return {
        "category": clean(g("lblExpClass")),
        "date_text": nfkc(g("lblExpDate")),
        "docno_text": nfkc(g("lblExpWord")),
        "agency_text": clean(g("lblExpDept")),
        "subject": clean(g("lblExpTitle")),
        "content": g("lblExpContent"),
        "memo": g("lblExpMemo"),
        "serial": serial.get("value") if serial else None,
    }


def parse_directory(html: str) -> list[dict]:
    doc = soup(html)
    out, seen = [], set()
    for a in doc.find_all("a", href=True):
        name = clean(a.get_text())
        href = urljoin(BASE, a["href"])
        if not name or len(name) < 3 or href in seen:
            continue
        m = re.search(r"LawDetail\.aspx\?id=(\d+)", href)
        if m:
            seen.add(href)
            out.append({"name": name, "rmis_law_id": int(m.group(1)), "url": href, "external": False})
        elif "law.moj.gov.tw" in href or "glrs.moi.gov.tw" in href:
            seen.add(href)
            out.append({"name": name, "url": href, "external": True})
    return out


def parse_law_detail(html: str) -> dict | None:
    doc = soup(html)
    name = by_id_suffix(doc, "ucLawDetailOut1_lblLawName")
    if name is None:
        return None
    arts = []
    for lab in doc.find_all(id=re.compile(r"dl4_lbl_ContentOrder_\d+$")):
        idx = re.search(r"_(\d+)$", lab["id"]).group(1)
        body = doc.find(id=re.compile(rf"dl4_lbl_Content_{idx}$"))
        label = nfkc(lab.get_text())
        key = article_key(label) or _point_key(label)
        if not key:
            continue
        arts.append({"key": key, "label": article_label(key) if article_key(label) else label,
                     "chapter": None, "text": _list_text(body)})
    hist = []
    for a in doc.find_all("a", id=re.compile(r"dl3_hlRelation_\d+$")):
        t = clean(a.get_text())
        m = re.search(r"id=(\d+)", a.get("href", ""))
        hist.append({"text": re.sub(r"^\d+、", "", t), "date": roc_to_iso(t), "rmis_history_id": int(m.group(1)) if m else None})
    att = []
    for lab in doc.find_all(id=re.compile(r"dl5_lbl_DocName_\d+$")):
        idx = re.search(r"_(\d+)$", lab["id"]).group(1)
        link = doc.find(id=re.compile(rf"dl5_hl_DocFile_{idx}$"))
        att.append({"name": clean(lab.get_text()), "url": urljoin(BASE, link["href"]) if link and link.get("href") else None})
    exp = by_id_suffix(doc, "ucLawDetailOut1_hl_LawExp")
    return {
        "name": clean(name.get_text()),
        "docno_text": clean(text_of(by_id_suffix(doc, "ucLawDetailOut1_lblLawCode"), False)),
        "date_text": nfkc(text_of(by_id_suffix(doc, "ucLawDetailOut1_lblLaw_Date"), False)),
        "articles": arts,
        "histories": hist,
        "attachments": att,
        "lawexp_url": urljoin(BASE, exp["href"]) if exp is not None and exp.get("href") else None,
    }


def _point_key(label: str) -> str | None:
    """行政規則 use 點: '一、' / '第1點' -> 'P1'."""
    from ..util import cn_to_int
    m = re.search(r"第?\s*([0-9一二三四五六七八九十百]+)(?:\s*[-之]\s*([0-9一二三四五六七八九十]+))?\s*[點、]", nfkc(label))
    if m and cn_to_int(m.group(1)) is not None:
        k = f"P{cn_to_int(m.group(1))}"
        if m.group(2) and cn_to_int(m.group(2)) is not None:
            k += f"-{cn_to_int(m.group(2))}"
        return k
    return None


def _list_text(node) -> str:
    """Keep <ol><li> numbering as 一、二、 like the official gazette text."""
    if node is None:
        return ""
    cn = "一二三四五六七八九十"
    for ol in node.find_all("ol"):
        for i, li in enumerate(ol.find_all("li", recursive=False), 1):
            prefix = (cn[i - 1] if i <= 10 else str(i)) + "、"
            li.insert(0, prefix)
    return text_of(node)


def parse_law_history(html: str) -> dict | None:
    doc = soup(html)
    name = by_id_suffix(doc, "ucLawHistoryDetailOut1_lblLawName")
    if name is None:
        return None
    content = text_of(by_id_suffix(doc, "ucLawHistoryDetailOut1_lbl_LawHistoryContent"))
    arts = split_fulltext_articles(content)
    return {
        "name": clean(name.get_text()),
        "docno_text": clean(text_of(by_id_suffix(doc, "ucLawHistoryDetailOut1_lblLawCode"), False)),
        "date": roc_to_iso(text_of(by_id_suffix(doc, "ucLawHistoryDetailOut1_lblLaw_Date"), False)),
        "content": content,
        "articles": arts if len(arts) >= 3 else [],
        "is_full_text": len(arts) >= 3,
    }


def parse_law_exp(html: str) -> dict | None:
    doc = soup(html)
    name = by_id_suffix(doc, "ucLawExpOut1_lblLawName")
    if name is None:
        return None
    items = []
    for w in doc.find_all(id=re.compile(r"dl4_lbl_exp_wprd_\d+$")):
        idx = re.search(r"_(\d+)$", w["id"]).group(1)
        items.append({
            "docno": normalize_docno(w.get_text()),
            "title": clean(text_of(doc.find(id=re.compile(rf"dl4_lbl_exp_title_{idx}$")), False)),
            "content": text_of(doc.find(id=re.compile(rf"dl4_lbl_exp_content_{idx}$"))),
        })
    return {"name": clean(name.get_text()), "items": items}


# ---------------------------------------------------------------- collectors
def interp_record(rmis_id: int, d: dict, list_row: dict | None) -> dict:
    url = f"{BASE}NewsDetail.aspx?id={rmis_id}"
    return {
        "source_key": f"rmis:{rmis_id}",
        "docno": normalize_docno(d["docno_text"]),
        "date": roc_to_iso(d["date_text"]),
        "date_text": d["date_text"],
        "agency_text": d.get("agency_text") or "",
        "category": d.get("category") or (list_row or {}).get("category") or "",
        "subject": d.get("subject") or (list_row or {}).get("subject") or "",
        "content": d.get("content") or "",
        "memo": d.get("memo") or "",
        "doc_class": "interpretation",
        "source": {"source_id": "rmis-interpretations", "url": url, "serial": d.get("serial"),
                   "fetched_at": now_iso()},
    }


class RmisInterpretations(Collector):
    source_id = "rmis-interpretations"
    kind = "interpretation"

    def collect(self, mode: str) -> CollectResult:
        res = CollectResult(self.source_id, self.kind)
        known: dict = self.cfg.get("_known", {})  # source_key -> {"list_hash", "last_synced"}
        daily_pages = int(self.cfg.get("daily_pages", 3))
        rows: list[dict] = []
        try:
            first, last = parse_news_list(self.client.get(BASE + "NewsList.aspx", expect_html=True).text)
        except SourceError as e:
            res.status, res.errors = getattr(e, "kind", "failed"), [str(e)]
            res.complete = False
            return res
        if not first:
            res.status, res.complete = "failed", False
            res.errors.append("列表頁解析不到任何資料（版面可能已變更）")
            return res
        rows.extend(first)
        pages = range(2, (last or 1) + 1) if mode in ("weekly", "monthly", "full") else range(2, daily_pages + 1)
        res.complete = mode in ("weekly", "monthly", "full")
        for p in pages:
            try:
                got, _ = parse_news_list(self.client.get(f"{BASE}NewsList.aspx?page={p}", expect_html=True).text)
                rows.extend(got)
            except SourceError as e:
                res.errors.append(f"page {p}: {e}")
                res.complete = False
        res.notes.append(f"列表頁數：{last}，本次讀取列表 {len(rows)} 筆")
        refetch_all = mode in ("monthly", "full")
        max_detail = int(self.cfg.get("max_detail_per_run", 2500))
        fetched = 0
        for row in rows:
            key = f"rmis:{row['rmis_id']}"
            lh = sha256([row["date_text"], row["docno_text"], row["subject"], row["category"]])
            k = known.get(key)
            if k and k.get("list_hash") == lh and not refetch_all:
                continue
            if fetched >= max_detail:
                res.complete = False
                res.notes.append("已達單次明細擷取上限，其餘於下次執行補足")
                break
            try:
                d = parse_news_detail(self.client.get(f"{BASE}NewsDetail.aspx?id={row['rmis_id']}", expect_html=True).text)
            except SourceError as e:
                res.errors.append(f"detail {row['rmis_id']}: {e}")
                continue
            fetched += 1
            if d is None:
                res.errors.append(f"detail {row['rmis_id']}: 明細頁無資料")
                continue
            rec = interp_record(row["rmis_id"], d, row)
            rec["list_hash"] = lh
            res.records.append(rec)
        res.notes.append(f"明細擷取 {fetched} 筆")
        res.extra = {"listed_keys": [f"rmis:{r['rmis_id']}" for r in rows]}  # type: ignore[attr-defined]
        res.requests = self.client.requests_made
        if res.errors:
            res.status = "partial"
        return res


class RmisLaws(Collector):
    """Laws hosted on RMIS (incl. 行政規則 not in the MOJ database) and their 歷史沿革 pages."""
    source_id = "rmis-laws"
    kind = "law"

    def collect(self, mode: str) -> CollectResult:
        res = CollectResult(self.source_id, self.kind)
        try:
            entries = parse_directory(self.client.get(BASE + "Directory.aspx", expect_html=True).text)
        except SourceError as e:
            res.status, res.complete, res.errors = "failed", False, [str(e)]
            return res
        local = [e for e in entries if not e["external"]]
        if len(local) < 5:
            res.status, res.complete = "failed", False
            res.errors.append(f"法規目錄僅解析到 {len(local)} 筆，疑似版面變更")
            return res
        known_hist: set = set(self.cfg.get("_known_history_ids", []))
        fetch_history = mode in ("weekly", "monthly", "full")
        for e in local:
            try:
                d = parse_law_detail(self.client.get(e["url"], expect_html=True).text)
            except SourceError as ex:
                res.errors.append(f"{e['name']}: {ex}")
                continue
            if not d or not d["articles"]:
                res.errors.append(f"{e['name']}: 法規內容解析失敗")
                continue
            versions = []
            if fetch_history:
                for h in d["histories"]:
                    hid = h.get("rmis_history_id")
                    if not hid or (hid in known_hist and mode != "full"):
                        continue
                    try:
                        hv = parse_law_history(self.client.get(f"{BASE}LawHistoryDetail.aspx?id={hid}", expect_html=True).text)
                    except SourceError as ex:
                        res.errors.append(f"history {hid}: {ex}")
                        continue
                    if hv:
                        hv.update(rmis_history_id=hid, url=f"{BASE}LawHistoryDetail.aspx?id={hid}", entry=h["text"])
                        versions.append(hv)
            level = "行政規則" if e["rmis_law_id"] >= 3000 else ("法律" if e["rmis_law_id"] < 2000 else "命令")
            res.records.append({
                "rmis_law_id": e["rmis_law_id"],
                "name": d["name"] or e["name"],
                "level": level,
                "docno_text": d["docno_text"],
                "modified_date": roc_to_iso(d["date_text"]),
                "articles": d["articles"],
                "histories": d["histories"],
                "attachments": d["attachments"],
                "lawexp_url": d["lawexp_url"],
                "versions": versions,
                "source": {"source_id": self.source_id, "url": e["url"], "fetched_at": now_iso()},
            })
        res.extra = {"external_links": [e for e in entries if e["external"]]}  # type: ignore[attr-defined]
        res.requests = self.client.requests_made
        if res.errors:
            res.status = "partial"
        return res


class RmisLawExp(Collector):
    source_id = "rmis-lawexp"
    kind = "relation"

    def collect(self, mode: str) -> CollectResult:
        res = CollectResult(self.source_id, self.kind)
        for law in self.cfg.get("_laws", []):  # [{"law_id", "lawexp_url"}]
            try:
                d = parse_law_exp(self.client.get(law["lawexp_url"], expect_html=True, timeout=120).text)
            except SourceError as ex:
                res.errors.append(f"{law['law_id']}: {ex}")
                continue
            if not d:
                continue
            for it in d["items"]:
                res.records.append({"law_id": law["law_id"], "docno": it["docno"], "title": it["title"],
                                    "content": it["content"], "evidence_url": law["lawexp_url"]})
        res.requests = self.client.requests_made
        if res.errors:
            res.status = "partial" if res.records else "failed"
        return res
