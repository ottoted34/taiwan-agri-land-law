"""Record validation. Invalid records are rejected and logged, never published."""
from __future__ import annotations

import re

ISO = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def validate_interpretation(r: dict) -> list[str]:
    errs = []
    if not r.get("docno") or "字第" not in r["docno"]:
        errs.append("發文字號缺漏或格式不符")
    if not r.get("date") or not ISO.match(r["date"]):
        errs.append(f"發文日期無法辨識：{r.get('date_text')}")
    elif not ("1945-01-01" <= r["date"] <= "2100-01-01"):
        errs.append("發文日期超出合理範圍")
    if not r.get("subject") and not r.get("content"):
        errs.append("主旨與內容皆為空")
    if not (r.get("source") or {}).get("url"):
        errs.append("缺少官方來源網址")
    if re.search(r"<\s*(html|script|body)", (r.get("content") or "")[:2000], re.I):
        errs.append("內容含 HTML 原始碼，疑似錯誤頁")
    return errs


def validate_law(r: dict) -> list[str]:
    errs = []
    if not r.get("name"):
        errs.append("法規名稱缺漏")
    if not r.get("articles"):
        errs.append("無任何條文")
    if r.get("modified_date") and not ISO.match(r["modified_date"]):
        errs.append("修正日期格式錯誤")
    keys = [a["key"] for a in r.get("articles", [])]
    if len(keys) != len(set(keys)):
        errs.append("條號重複")
    if not (r.get("source") or {}).get("url"):
        errs.append("缺少官方來源網址")
    return errs


def validate_technical(r: dict) -> list[str]:
    errs = []
    if not r.get("title"):
        errs.append("標題缺漏")
    if r.get("date") and not ISO.match(r["date"]):
        errs.append("日期格式錯誤")
    if r.get("url") and not str(r["url"]).startswith(("http://", "https://")):
        errs.append("連結不是網址")
    return errs


VALIDATORS = {"interpretation": validate_interpretation, "law": validate_law, "technical": validate_technical}
