"""Tiny HTML helpers built on BeautifulSoup."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .util import clean


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def text_of(node, keep_breaks: bool = True) -> str:
    if node is None:
        return ""
    if keep_breaks:
        for br in node.find_all("br"):
            br.replace_with("\n")
        for tag in node.find_all(["p", "li", "div"]):
            tag.append("\n")
    t = node.get_text("")
    t = t.replace("\r", "")
    lines = [clean(x) for x in t.split("\n")]
    out, blank = [], False
    for ln in lines:
        if ln:
            out.append(ln)
            blank = False
        elif not blank and out:
            out.append("")
            blank = True
    return "\n".join(out).strip()


def by_id_suffix(doc, suffix: str):
    return doc.find(id=re.compile(re.escape(suffix) + "$"))
