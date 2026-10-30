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
