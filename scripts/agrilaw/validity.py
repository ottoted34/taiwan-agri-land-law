"""Validity (效力) bookkeeping for interpretations — rule based, evidence first.
The system NEVER declares a letter "valid". Default status means only that no cessation
information has been found in the collected official material."""
from __future__ import annotations

import re

from .util import find_docnos, nfkc

STATUS_LABELS = {
    "no_known_cessation": "已確認存在，尚無已查得之停止適用資訊",
    "ceased": "官方明確停止適用",
    "revoked": "官方明確廢止或撤回",
    "amended_by_later": "後續函釋有變更或補充",
    "possibly_affected": "可能受法規修正影響",
    "needs_review": "效力待人工查核",
}

CEASE_RE = re.compile(r"(停止適用|不再適用|不再援用|停止援用|廢止|撤銷|撤回|不再引用|免再適用)")
AMEND_RE = re.compile(r"(補充|修正|變更|更正)")


def cessation_signals(rec: dict) -> list[dict]:
    """Find other letters this letter says are ceased / amended. Sentence-level, conservative."""
    text = nfkc(rec.get("subject", "") + "。" + rec.get("content", ""))
    own = rec.get("docno")
    out = []
    for sent in re.split(r"[。；\n]", text):
        nos = [d for d in find_docnos(sent) if d != own]
        if not nos:
            continue
        m = CEASE_RE.search(sent)
        if m and ("停止適用" in sent or "不再" in sent or rec.get("category") == "停止適用"):
            out += [{"target": d, "kind": "cease", "phrase": sent[:200]} for d in nos]
        elif re.search(r"(前開|上開|前揭).{0,30}(函|號).{0,20}(補充|修正|變更)", sent) or (AMEND_RE.search(sent) and "函釋" in sent and "說明" not in sent[:4]):
            out += [{"target": d, "kind": "amend", "phrase": sent[:200]} for d in nos]
    return out


def history_articles(entry_text: str) -> set[str] | str:
    """'修正發布第6、23、27～30條' -> {'6','23','27','28','29','30'}; '修正發布全文' -> 'ALL'."""
    from .util import cn_to_int
    t = nfkc(entry_text)
    if re.search(r"權責事項|改由.{0,10}管轄", t):  # jurisdiction transfer notice, no text amendment
        return set()
    if re.search(r"全文|名稱及全文", t):
        return "ALL"
    out: set[str] = set()
    for seg in re.findall(r"第\s*([0-9０-９一二三四五六七八九十百、，,～~\-至及之\s]+)\s*條", t):
        for part in re.split(r"[、，,及]", seg):
            part = part.strip()
            rng = re.split(r"[～~至]", part)
            if len(rng) == 2:
                a, b = cn_to_int(rng[0].replace("-", "")), cn_to_int(rng[1].replace("-", ""))
                if a and b and b >= a and b - a < 200:
                    out.update(str(x) for x in range(a, b + 1))
                continue
            m = re.match(r"([0-9一二三四五六七八九十百]+)(?:\s*[-之]\s*([0-9一二三四五六七八九十]+))?", part)
            if m and cn_to_int(m.group(1)):
                k = str(cn_to_int(m.group(1)))
                if m.group(2) and cn_to_int(m.group(2)):
                    k += f"-{cn_to_int(m.group(2))}"
                out.add(k)
    return out
