"""Diagnostics for maintainers: crawl the RMIS list and report pages whose row count looks wrong.
Writes into an output folder (uploaded as a workflow artifact, never committed)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .collectors.rmis import BASE, parse_news_list
from .http import Client


def rmis_list(out: Path, max_pages: int | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    c = Client()
    first = c.get(BASE + "NewsList.aspx", expect_html=True).text
    rows, last = parse_news_list(first)
    report = {"last_page": last, "pages": {}}
    for p in range(1, (max_pages or last or 1) + 1):
        html = first if p == 1 else c.get(f"{BASE}NewsList.aspx?page={p}", expect_html=True).text
        rows, _ = parse_news_list(html)
        rownums = re.findall(r'lvList_lblRowNum_\d+">\s*(\d+)', html)
        report["pages"][p] = {"parsed": len(rows), "rownum_spans": len(rownums), "first_rownum": rownums[0] if rownums else None,
                              "last_rownum": rownums[-1] if rownums else None, "ids": [r["rmis_id"] for r in rows]}
        if len(rows) != len(rownums) or (len(rows) < 10 and p != last):
            (out / f"rmis-list-p{p}.html").write_text(html, encoding="utf-8")
    all_ids = [i for v in report["pages"].values() for i in v["ids"]]
    report["total_rows"] = len(all_ids)
    report["unique_ids"] = len(set(all_ids))
    report["anomalous_pages"] = [p for p, v in report["pages"].items() if v["parsed"] != v["rownum_spans"] or (v["parsed"] < 10 and p != last)]
    (out / "rmis-list-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return {k: report[k] for k in ("last_page", "total_rows", "unique_ids", "anomalous_pages")}


def probe(out: Path, urls: list[str], follow: str = "") -> dict:
    """Source evaluation: fetch robots.txt and each URL (only where robots allows) and save the raw
    responses so a maintainer can decide whether a source may be collected automatically.
    `follow` is a regex: same-host links on fetched pages whose text or href matches are fetched too (one level)."""
    from urllib.parse import urljoin, urlparse

    from .html import soup
    from .http import RobotsDisallowed, SourceError

    out.mkdir(parents=True, exist_ok=True)
    c = Client(min_interval=2.0, timeout=40, retries=1)
    report: dict = {"robots": {}, "pages": []}
    queue, seen = list(urls), set()
    for depth in (0, 1):
        nxt = []
        for url in queue:
            if url in seen or len(seen) >= 60:
                continue
            seen.add(url)
            host = urlparse(url).netloc
            if host not in report["robots"]:
                try:
                    r = c.s.get(f"https://{host}/robots.txt", timeout=40)
                    report["robots"][host] = {"status": r.status_code, "text": r.text[:4000] if r.status_code == 200 else ""}
                except Exception as e:  # noqa: BLE001
                    report["robots"][host] = {"error": f"{type(e).__name__}: {e}"[:300]}
            entry: dict = {"url": url, "depth": depth}
            try:
                resp = c.get(url, expect_html=False)
                try:
                    text = resp.content.decode("utf-8")
                except UnicodeDecodeError:
                    text = resp.content.decode("big5", "replace")
                name = f"p{len(report['pages']):02d}.html"
                (out / name).write_text(text[:400000], encoding="utf-8")
                entry.update(status=resp.status, final_url=resp.url, file=name, bytes=len(resp.content),
                             content_type=resp.headers.get("Content-Type"))
                if depth == 0 and follow and "html" in (resp.headers.get("Content-Type") or ""):
                    d = soup(text)
                    for a in d.find_all("a", href=True):
                        href = urljoin(resp.url, a["href"])
                        if urlparse(href).netloc == host and re.search(follow, (a.get_text(" ") or "") + " " + href):
                            nxt.append(href)
                    entry["links"] = [{"t": (a.get_text(" ") or "").strip()[:60], "h": urljoin(resp.url, a["href"])}
                                      for a in d.find_all("a", href=True)][:400]
            except RobotsDisallowed:
                entry["robots_disallowed"] = True
            except SourceError as e:
                entry["error"] = str(e)[:300]
            except Exception as e:  # noqa: BLE001
                entry["error"] = f"{type(e).__name__}: {e}"[:300]
            report["pages"].append(entry)
        queue = nxt[:40]
    (out / "probe-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"pages": len(report["pages"]), "robots": {h: v.get("status", v.get("error")) for h, v in report["robots"].items()}}
