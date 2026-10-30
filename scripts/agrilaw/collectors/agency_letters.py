"""其他農業部所屬機關網站之函釋專區（2026-10-30 經 Repository 擁有者同意收錄）：
  ForestLetters : 林業及自然保育署「公文函釋」 https://www.forest.gov.tw/0000062
  TalisLetters  : 農業綠能發展資訊網「農業綠能函釋查詢」 https://talis.moa.gov.tw/age/
兩站皆無 robots.txt（每次擷取前仍由 http.Client 重新檢查）。只抓列表＋未收錄之明細；
monthly/full 模式重新比對全部明細。與既有函釋之合併在 sync.apply_agency_letters 處理。"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..html import soup
from ..http import SourceError
from ..util import clean, nfkc, normalize_docno, now_iso, roc_to_iso, sha256
from .base import CollectResult, Collector

FOREST = "https://www.forest.gov.tw/"
TALIS = "https://talis.moa.gov.tw/age/"
TALIS_LIST = TALIS + "Page/List?group=Regulation&category=Explanation"

# 林保署函釋以野生動物保育、林產等為多；只收錄與農地審查相關者（列表之法規名稱＋主旨比對；2026-10-30 擁有者指定）
FOREST_KEYWORDS = ["山坡地", "林業用地", "農業用地", "農牧用地", "容許使用", "林業設施", "農業設施", "回饋金"]


def _lines(node) -> str:
    """Keep paragraph / <br> structure, drop the inline line breaks Word-pasted HTML carries."""
    if node is None:
        return ""
    for br in node.find_all("br"):
        br.replace_with("\n")
    for tag in node.find_all(["p", "div", "li", "tr"]):
        tag.insert_after("\n")
    t = node.get_text("").replace("\r", "")
    out = [clean(x) for x in t.split("\n")]
    return "\n".join(x for x in out if x)


# ---------------------------------------------------------------- forest
def parse_forest_list(html: str) -> tuple[list[dict], int | None]:
    doc = soup(html)
    rows = []
    for a in doc.select("li.commonList-item a.newsItem[href]"):
        m = re.search(r"/0000062/(\d+)", a["href"])
        if not m:
            continue
        cats = [clean(s.get_text()) for s in a.select(".category span")]
        meta = {k: clean(v) for li in a.select("ul.rect-list li") for k, _, v in [li.get_text().partition("：")]}
        title = a.select_one(".newsItem__content-title")
        rows.append({"item_id": m.group(1), "url": urljoin(FOREST, a["href"]), "unit": cats[0] if cats else "",
                     "law": cats[1] if len(cats) > 1 else "", "subject": clean(title.get_text()) if title else "",
                     "date_text": meta.get("發佈日期", ""), "docno_text": meta.get("發文文號", "")})
    last = None
    for x in doc.find_all("a", href=True):
        m = re.search(r"0000062\?Do=Q&p=(\d+)", x["href"].replace("&amp;", "&"))
        if m:
            last = max(last or 0, int(m.group(1)))
    return rows, last


def parse_forest_detail(html: str) -> dict | None:
    doc = soup(html)
    h1 = doc.select_one(".page-title h1")
    art = doc.select_one("article.page-article")
    if h1 is None or art is None:
        return None
    meta = {k: clean(v) for li in doc.select("#content ul.rect-list li, .newsItem__content ul.rect-list li")
            for k, _, v in [li.get_text().partition("：")]}
    cats = [clean(s.get_text()) for s in doc.select(".newsItem__content .category span")]
    return {"subject": clean(h1.get_text()), "content": _lines(art), "date_text": meta.get("發佈日期", ""),
            "docno_text": meta.get("發文文號", ""), "unit": cats[0] if cats else "", "law": cats[1] if len(cats) > 1 else ""}


def forest_relevant(row: dict) -> bool:
    t = row.get("law", "") + row.get("subject", "")
    return any(k in t for k in FOREST_KEYWORDS)


# ---------------------------------------------------------------- talis
def parse_talis_list(html: str) -> tuple[list[dict], int | None]:
    doc = soup(html)
    rows, seen = [], set()
    for a in doc.find_all("a", href=True):
        m = re.search(r"/age/Page/Content/([0-9a-f-]{36})\?group=Regulation&category=Explanation", a["href"].replace("&amp;", "&"))
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        txt = clean(a.get_text(" "))
        dm = re.search(r"發布時間[:：]\s*(\d{4}-\d{2}-\d{2})", txt)
        rows.append({"item_id": m.group(1), "url": urljoin(TALIS, a["href"]),
                     "subject": clean(re.sub(r"發布時間[:：].*$", "", txt)), "posted": dm.group(1) if dm else None})
    last = None
    for x in doc.find_all("a", href=True):
        m = re.search(r"[?&]page=(\d+)", x["href"])
        if m and "category=Explanation" in x["href"]:
            last = max(last or 0, int(m.group(1)))
    return rows, last


def parse_talis_detail(html: str) -> dict | None:
    doc = soup(html)
    post = doc.select_one("div.post")
    h1 = post.select_one(".p-title h1") if post else None
    if h1 is None:
        return None
    subject = clean(h1.get_text())
    meta_div = next((d for d in post.find_all("div") if d.find(string=re.compile("發文字號"))), None)
    full = nfkc(post.get_text(" "))
    dn = re.search(r"發文字號[:：]\s*(\S+號)", full)
    dt = re.search(r"發文日期[:：]\s*(中華民國\s*\d+\s*年\s*\d+\s*月\s*\d+\s*日|\d{2,3}[./-]\d{1,2}[./-]\d{1,2})", full)
    for tag in post.select(".p-title"):
        tag.decompose()
    if meta_div is not None:
        meta_div.decompose()
    for a in post.find_all("a"):
        if clean(a.get_text()) == "返回":
            a.decompose()
    return {"subject": subject, "docno_text": dn.group(1) if dn else "", "date_text": dt.group(1) if dt else "",
            "content": _lines(post)}


# ---------------------------------------------------------------- collectors
class _ListDetail(Collector):
    kind = "interpretation"
    daily_pages = 2
    prefix = ""

    def list_url(self, page: int) -> str:
        raise NotImplementedError

    def parse_list(self, html):
        raise NotImplementedError

    def parse_detail(self, html):
        raise NotImplementedError

    def keep(self, row: dict) -> bool:
        return True

    def to_raw(self, row: dict, det: dict) -> dict:
        raise NotImplementedError

    def collect(self, mode: str) -> CollectResult:
        res = CollectResult(self.source_id, self.kind)
        known = set(self.cfg.get("_known", []))
        refetch = mode in ("monthly", "full")
        try:
            first = self.client.get(self.list_url(1), expect_html=True).text
        except SourceError as e:
            res.status, res.complete = "failed", False
            res.errors.append(str(e))
            return res
        rows, last = self.parse_list(first)
        last = last or 1
        pages = last if mode != "daily" else min(self.daily_pages, last)
        for p in range(2, pages + 1):
            try:
                more, _ = self.parse_list(self.client.get(self.list_url(p), expect_html=True).text)
                rows += more
            except SourceError as e:
                res.errors.append(f"列表第 {p} 頁：{e}")
        res.complete = pages >= last and not res.errors
        listed = [r for r in rows if self.keep(r)]
        res.extra["listed_keys"] = [f"{self.prefix}:{r['item_id']}" for r in listed]
        res.notes.append(f"列表 {last} 頁，本次讀取 {pages} 頁、{len(rows)} 筆，符合收錄範圍 {len(listed)} 筆")
        for r in listed:
            sk = f"{self.prefix}:{r['item_id']}"
            if sk in known and not refetch:
                continue
            try:
                det = self.parse_detail(self.client.get(r["url"], expect_html=True).text)
            except SourceError as e:
                res.errors.append(f"{sk}: {e}")
                continue
            if det is None:
                res.errors.append(f"{sk}: 明細頁解析失敗")
                continue
            raw = self.to_raw(r, det)
            raw["source_key"] = sk
            raw["source"] = {"source_id": self.source_id, "url": r["url"], "fetched_at": now_iso()}
            raw["list_hash"] = sha256(r)
            res.records.append(raw)
        if res.errors:
            res.status = "partial" if res.records or rows else "failed"
        return res


class ForestLetters(_ListDetail):
    source_id = "forest-interpretations"
    prefix = "forest"
    daily_pages = 3

    def list_url(self, page: int) -> str:
        return FOREST + "0000062" + (f"?Do=Q&p={page}" if page > 1 else "")

    def parse_list(self, html):
        return parse_forest_list(html)

    def parse_detail(self, html):
        return parse_forest_detail(html)

    def keep(self, row):
        return forest_relevant(row)

    def to_raw(self, row, det):
        docno_text = det["docno_text"] or row["docno_text"]
        date_text = det["date_text"] or row["date_text"]
        return {"docno": normalize_docno(docno_text), "docno_text": docno_text, "date": roc_to_iso(date_text), "date_text": date_text,
                "agency_text": "", "category": "／".join(x for x in (det["unit"] or row["unit"], det["law"] or row["law"]) if x),
                "subject": det["subject"] or row["subject"], "content": det["content"],
                "memo": "林業及自然保育署公文函釋專區"}


class TalisLetters(_ListDetail):
    source_id = "talis-green-energy"
    prefix = "talis"

    def list_url(self, page: int) -> str:
        return TALIS_LIST if page == 1 else f"{TALIS}Page/List?page={page}&group=Regulation&category=Explanation"

    def parse_list(self, html):
        return parse_talis_list(html)

    def parse_detail(self, html):
        return parse_talis_detail(html)

    def to_raw(self, row, det):
        date = roc_to_iso(det["date_text"])
        return {"docno": normalize_docno(det["docno_text"]), "docno_text": det["docno_text"], "date": date,
                "date_text": det["date_text"], "agency_text": "", "category": "農業綠能",
                "subject": det["subject"] or row["subject"], "content": det["content"],
                "memo": f"農業綠能發展資訊網函釋查詢（網站發布時間 {row['posted']}）" if row.get("posted") else "農業綠能發展資訊網函釋查詢"}
