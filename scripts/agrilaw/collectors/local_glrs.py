"""地方法規共用系統（縣市政府「主管法規共用系統」，頁面為 LawContent.aspx?id=GLxxxxxx）。
只擷取管理者在 config/local/counties.yaml 審核列入之法規；類別頁另行列出「待審核候選」，
候選不會自動上線。每次擷取前由 http.Client 檢查 robots.txt。"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from ..articles import article_key, article_label
from ..html import soup
from ..http import SourceError
from ..util import clean, cn_to_int, nfkc, now_iso, roc_to_iso
from .base import CollectResult, Collector

_LABEL = re.compile(r"^\s*(第\s*[0-9一二三四五六七八九十百零〇]+\s*條(?:\s*之\s*[一二三四五六七八九十0-9]+)?)[\s　]*")
_POINT = re.compile(r"^\s*([一二三四五六七八九十百]+)(?:\s*之\s*([一二三四五六七八九十]+))?\s*、[\s　]*")
_PARA_START = re.compile(r"^(（?[一二三四五六七八九十]+[）、]|\(\s*[一二三四五六七八九十0-9]+\s*\)|[0-9]+[.、]|前項|前二項|第[一二三四五六七八九十]+項)")


def _join_lines(lines: list[str]) -> str:
    """官方頁面以固定欄寬換行並以全形空白縮排。前一行以句號、冒號、分號結束或本行為款目／新項時才分段，其餘接續。"""
    out: list[str] = []
    for raw in lines:
        s = raw.replace("\xa0", " ").strip(" 　\t")
        if not s:
            continue
        if out and not re.search(r"[。：:；;]$", out[-1]) and not _PARA_START.match(s):
            out[-1] += s
        else:
            out.append(s)
    return "\n".join(out)


def parse_glrs_law(html: str, url: str) -> dict | None:
    doc = soup(html)
    head: dict[str, str] = {}
    att = []
    for tr in doc.find_all("tr"):
        th = tr.find("th")
        td = tr.find("td")
        if not th or not td:
            continue
        k = clean(th.get_text()).rstrip("：:")
        if k == "圖表附件":
            for a in td.find_all("a", href=True):
                att.append({"name": clean(a.get_text()), "url": urljoin(url, a["href"])})
        else:
            for d in td.find_all("div"):
                if clean(d.get_text()):
                    head[k + "_note"] = clean(d.get_text())
                d.extract()
            head[k] = clean(td.get_text(" "))
    name = head.get("法規名稱")
    if not name:
        return None
    table = doc.find(id=re.compile(r"tableLawArticle"))
    arts, chapter, preface = [], None, []
    for tr in (table.find_all("tr") if table else []):
        tds = tr.find_all("td")
        if len(tds) == 1 or (tds and "law-char" in " ".join(tds[0].get("class", []))):
            chapter = clean(tds[0].get_text()) or chapter
            continue
        body = tds[-1] if tds else None
        if body is None:
            continue
        for br in body.find_all("br"):
            br.replace_with("\n")
        for p in body.find_all("p"):
            p.append("\n")
        text = _join_lines(body.get_text("").split("\n"))
        if not text:
            continue
        first = nfkc(text.split("\n", 1)[0])
        m = _LABEL.match(text)
        if m and article_key(m.group(1)):
            key = article_key(m.group(1))
            arts.append({"key": key, "label": article_label(key), "chapter": chapter, "text": text[m.end():].strip()})
            continue
        m = _POINT.match(text)
        if m and cn_to_int(m.group(1)) is not None:
            key = f"P{cn_to_int(m.group(1))}" + (f"-{cn_to_int(m.group(2))}" if m.group(2) and cn_to_int(m.group(2)) else "")
            arts.append({"key": key, "label": f"第 {key[1:]} 點", "chapter": chapter, "text": text[m.end():].strip()})
            continue
        if arts:  # 無標號之續行
            arts[-1]["text"] += "\n" + text
        else:
            preface.append(first if len(text) > 400 else text)
    system = head.get("法規體系", "")
    level = system.split("/")[-1] if "/" in system else system
    status = "current"
    if re.search(r"廢止|停止適用", head.get("公發布日_note", "") + head.get("法規名稱_note", "") + name):
        status = "abolished"
    return {
        "name": name, "published_date": roc_to_iso(head.get("公發布日")), "modified_date": roc_to_iso(head.get("修正日期")) or roc_to_iso(head.get("公發布日")),
        "docno_text": head.get("發文字號", ""), "system_path": system, "level": level or "地方法規", "status": status,
        "status_note": head.get("公發布日_note", ""), "attachments": att, "articles": arts, "foreword": "\n".join(preface)[:4000],
    }


def parse_glrs_history(html: str) -> list[dict]:
    doc = soup(html)
    box = doc.find(id=re.compile(r"divLawContentSource$"))
    if box is None:
        return []
    for br in box.find_all("br"):
        br.replace_with("\n")
    out = []
    for line in box.get_text("").split("\n"):
        t = re.sub(r"^\s*\d+\s*[.、]\s*", "", clean(line))
        if t:
            out.append({"text": t, "date": roc_to_iso(t)})
    return out


def parse_glrs_category(html: str, url: str) -> list[dict]:
    doc = soup(html)
    out, seen = [], set()
    for a in doc.find_all("a", href=True):
        m = re.search(r"LawContent\.aspx\?id=(\w+)", a["href"])
        name = clean(a.get_text())
        if m and name and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append({"law_system_id": m.group(1), "name": name, "url": urljoin(url, a["href"])})
    return out


class GlrsLocalLaws(Collector):
    """cfg: county(dict from counties.yaml)."""
    kind = "law"

    def __init__(self, cfg: dict, client):
        super().__init__(cfg, client)
        self.county = cfg["county"]
        self.source_id = self.county["source_id"]

    def collect(self, mode: str) -> CollectResult:
        c = self.county
        res = CollectResult(self.source_id, self.kind)
        if not c.get("auto_sync"):
            res.status = "unavailable"
            res.errors.append(f"{c['name']} 未設定自動同步（auto_sync=false），僅收錄人工建立之資料")
            return res
        base = c["law_system"].rstrip("/") + "/"
        for item in c.get("laws", []):
            gid = item["law_system_id"]
            url = f"{base}LawContent.aspx?id={gid}"
            try:
                page = self.client.get(url, expect_html=True)
                rec = parse_glrs_law(page.text, url)
                if rec is None:
                    res.errors.append(f"{gid} 解析失敗（找不到法規名稱）")
                    continue
                if item.get("name") and nfkc(item["name"]) != nfkc(rec["name"]):
                    res.notes.append(f"{gid} 官方名稱「{rec['name']}」與設定「{item['name']}」不同（可能已修正名稱），以官方為準")
                try:
                    hp = self.client.get(f"{base}LawContentSource.aspx?id={gid}", expect_html=True)
                    rec["histories"] = parse_glrs_history(hp.text)
                except SourceError as e:
                    rec["histories"] = []
                    res.notes.append(f"{gid} 沿革頁無法取得：{e}")
                rec.update({"law_system_id": gid, "county": c["name"], "config": item,
                            "source": {"source_id": self.source_id, "url": url, "fetched_at": now_iso()}})
                res.records.append(rec)
            except SourceError as e:
                res.errors.append(f"{gid}: {e}")
        # 候選清單（只供管理者審核，不會自動收錄）
        cands = []
        for cat in c.get("candidate_categories", []):
            todo, done = [urljoin(base, cat)], set()
            while todo and len(done) < 30:
                u = todo.pop(0)
                done.add(u)
                try:
                    page = self.client.get(u, expect_html=True)
                except SourceError as e:
                    res.notes.append(f"候選類別頁無法取得：{e}")
                    break
                cands += parse_glrs_category(page.text, page.url)
                for a in soup(page.text).find_all("a", href=True):
                    nxt = urljoin(page.url, a["href"])
                    if "page=" in nxt and "media=print" not in nxt and "LawCategoryContentList" in nxt and nxt not in done and nxt not in todo:
                        todo.append(nxt)
        kw = c.get("candidate_keywords") or []
        listed = {i["law_system_id"] for i in c.get("laws", [])} | set(c.get("rejected", []) or [])
        cands = list({x["law_system_id"]: x for x in cands}.values())
        res.extra["candidates"] = [x for x in cands if x["law_system_id"] not in listed and (not kw or any(k in x["name"] for k in kw))]
        if res.errors and not res.records:
            res.status = "failed"
        elif res.errors:
            res.status = "partial"
        res.complete = not res.errors
        return res
