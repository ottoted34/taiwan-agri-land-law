"""Derived data recomputed after every sync: relations, validity signals, amendment impact,
topic tags. Only writes records whose derived fields actually changed (small git diffs)."""
from __future__ import annotations

from . import paths
from .relations import extract_refs, law_name_map, manual_entries
from .store import Store
from .util import load_yaml, normalize_docno, now_iso, read_json, sha256, write_json
from .validity import cessation_signals, history_articles

DERIVED = ("validity", "topics", "flags", "relations")


def _topics(text: str, table: dict) -> list[str]:
    return [k for k, v in table.items() if any(kw in text for kw in v["keywords"])]


def postprocess() -> dict:
    laws_store, it_store, tech_store = Store(paths.LAWS), Store(paths.INTERP), Store(paths.TECH)
    laws = list(laws_store.all())
    interps = list(it_store.all())
    topics_cfg = load_yaml(paths.CONFIG / "topics" / "topics.yaml")
    names = law_name_map(laws)
    law_by_id = {l["id"]: l for l in laws}
    by_docno: dict[str, list[dict]] = {}
    for r in interps:
        by_docno.setdefault(r["docno"], []).append(r)

    # --- relations
    official = (read_json(paths.RELATIONS / "official.json", {}) or {}).get("relations", [])
    man = manual_entries()
    rel_by_interp: dict[str, list[dict]] = {}
    for o in official:
        rel_by_interp.setdefault(o["interp_id"], []).append({"law_id": o["law_id"], "article": None, "kind": "official",
                                                              "evidence": o["evidence"]})
    extracted_all = []
    for r in interps:
        refs = extract_refs(r.get("subject", "") + "\n" + r.get("content", ""), names)
        for ref in refs:
            item = {"law_id": ref["law_id"], "article": ref["article"], "kind": "extracted", "snippet": ref["snippet"]}
            rel_by_interp.setdefault(r["id"], []).append(item)
            extracted_all.append({"interp_id": r["id"], **item})
    name_to_id = {l["name"]: l["id"] for l in laws}
    for m in man.get("relations") or []:
        for r in by_docno.get(normalize_docno(m["docno"]), []):
            lid = name_to_id.get(m["law"])
            if lid:
                rel_by_interp.setdefault(r["id"], []).append({"law_id": lid, "article": str(m.get("article") or "") or None,
                                                              "kind": "manual", "evidence": m.get("evidence"),
                                                              "note": m.get("note"), "confirmed_by": m.get("confirmed_by")})
    write_json(paths.RELATIONS / "extracted.json", {"generated_at": now_iso(), "relations": extracted_all}, compact=True)

    # --- cessation / amendment signals between letters
    signals: dict[str, list[dict]] = {}
    for r in interps:
        for s in cessation_signals(r):
            for t in by_docno.get(s["target"], []):
                if t["id"] != r["id"] and (t.get("date") or "") <= (r.get("date") or "9999"):
                    signals.setdefault(t["id"], []).append({"by_id": r["id"], "by_docno": r["docno"], "by_date": r["date"],
                                                            "kind": s["kind"], "phrase": s["phrase"]})
    manual_validity = {}
    for v in man.get("validity") or []:
        manual_validity[(normalize_docno(v["docno"]), v.get("date"))] = v

    # --- amendment impact
    def law_amendments(lid: str) -> list[dict]:
        l = law_by_id.get(lid) or {}
        hs = [{"date": h.get("date"), "text": h.get("text", "")} for h in l.get("histories", [])]
        hs += [{"date": h.get("date"), "text": h.get("text", "")} for h in (l.get("rmis") or {}).get("histories", [])]
        seen, out = set(), []
        for h in hs:
            if h["date"] and (h["date"], h["text"][:30]) not in seen:
                seen.add((h["date"], h["text"][:30]))
                out.append(h)
        return out

    amend_cache = {lid: law_amendments(lid) for lid in law_by_id}
    changed = 0
    for r in interps:
        rels = rel_by_interp.get(r["id"], [])
        # dedupe relations
        uniq, seen = [], set()
        for x in rels:
            k = (x["law_id"], x.get("article"), x["kind"])
            if k not in seen:
                seen.add(k)
                uniq.append(x)
        impacts = []
        for x in uniq:
            for h in amend_cache.get(x["law_id"], []):
                if not r.get("date") or h["date"] <= r["date"]:
                    continue
                arts = history_articles(h["text"])
                hit = arts == "ALL" or (x.get("article") and x["article"] in arts)
                if hit:
                    impacts.append({"law_id": x["law_id"], "law_name": law_by_id[x["law_id"]]["name"],
                                    "article": x.get("article"), "amended_on": h["date"], "history": h["text"][:160],
                                    "relation_kind": x["kind"]})
        # de-duplicate impacts
        imp_u, s2 = [], set()
        for i in impacts:
            k = (i["law_id"], i["article"], i["amended_on"])
            if k not in s2:
                s2.add(k)
                imp_u.append(i)
        sig = signals.get(r["id"], [])
        mv = manual_validity.get((r["docno"], r.get("date"))) or manual_validity.get((r["docno"], None))
        if mv:
            validity = {"status": mv["status"], "confirmed": True, "basis": [{"type": "manual", "text": mv.get("basis"),
                        "evidence": mv.get("evidence"), "by": mv.get("confirmed_by"), "at": mv.get("confirmed_at")}]}
        elif any(s["kind"] == "cease" for s in sig):
            validity = {"status": "needs_review", "confirmed": False,
                        "basis": [{"type": "cessation_signal", **s} for s in sig]}
        elif sig:
            validity = {"status": "amended_by_later", "confirmed": False, "basis": [{"type": "amend_signal", **s} for s in sig]}
        elif imp_u:
            validity = {"status": "possibly_affected", "confirmed": False, "basis": [{"type": "law_amendment", **i} for i in imp_u[:10]]}
        else:
            validity = {"status": "no_known_cessation", "confirmed": False, "basis": []}
        if r.get("category") == "停止適用":
            validity.setdefault("notes", []).append("本文件為停止適用公告")
        text = (r.get("subject") or "") + (r.get("content") or "")
        topics = _topics(text, topics_cfg["legal_topics"])
        flags = []
        if r.get("is_historical"):
            flags.append("historical_agency")
        if r.get("source_missing_since"):
            flags.append("source_missing")
        if len(by_docno.get(r["docno"], [])) > 1:
            flags.append("docno_shared")
        derived = {"validity": validity, "topics": topics, "flags": flags, "relations": uniq}
        if sha256({k: r.get(k) for k in DERIVED}) != sha256(derived):
            r.update(derived)
            it_store.put(r)
            changed += 1

    # --- technical topics
    tchanged = 0
    for t in tech_store.all():
        tp = _topics((t.get("title") or "") + (t.get("series") or ""), topics_cfg["technical_topics"])
        if tp != t.get("topics"):
            t["topics"] = tp
            tech_store.put(t)
            tchanged += 1
    status_counts: dict[str, int] = {}
    for r in it_store.all():
        s = (r.get("validity") or {}).get("status")
        status_counts[s] = status_counts.get(s, 0) + 1
    return {"interpretations_updated": changed, "technical_updated": tchanged, "validity_counts": status_counts,
            "relations_extracted": len(extracted_all), "relations_official": len(official)}
