"""Build static data for the website (web/public/data). Regenerated from data/ on every deploy,
so the search index can always be rebuilt and never becomes a second source of truth."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta

from . import paths
from .agencies import registry
from .store import Store
from .util import TW, load_yaml, now_iso, read_json, write_json
from .validity import STATUS_LABELS

DAILY_SOURCES = ["moj-law-api", "rmis-interpretations", "rmis-laws"]


def build() -> dict:
    out = paths.WEB_DATA
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    laws = sorted(Store(paths.LAWS).all(), key=lambda l: (not l.get("core"), l["name"]))
    interps = sorted(Store(paths.INTERP).all(), key=lambda r: r.get("date") or "", reverse=True)
    techs = sorted(Store(paths.TECH).all(), key=lambda r: r.get("date") or "", reverse=True)
    reg = registry()
    agencies = reg["agencies"]
    law_names = {l["id"]: l["name"] for l in laws}

    # ---- laws
    law_index = []
    for l in laws:
        versions = []
        vdir = paths.LAWS / "versions" / l["id"]
        if vdir.exists():
            for p in sorted(vdir.glob("*.json")):
                v = read_json(p)
                versions.append({"id": v["version_id"], "date": v.get("modified_date"), "kind": v["kind"],
                                 "full": v.get("is_full_text"), "entry": v.get("entry") or v.get("note"),
                                 "url": v.get("url")})
                write_json(out / "versions" / l["id"] / f"{v['version_id']}.json", v, compact=True)
        versions.sort(key=lambda v: (v["date"] or "", v["kind"] != "captured"))
        detail = {k: l.get(k) for k in ("id", "name", "level", "category", "official_url", "modified_date", "effective_date",
                                        "effective_note", "abandon_note", "status", "histories", "articles", "attachments",
                                        "topics", "core", "sources", "primary_source", "rmis", "cross_check", "flags",
                                        "former_names", "last_checked", "last_changed", "first_seen", "change_log", "foreword")}
        detail["versions"] = versions
        write_json(out / "laws" / f"{l['id']}.json", detail, compact=True)
        law_index.append({"id": l["id"], "n": l["name"], "lv": l.get("level"), "st": l.get("status"), "md": l.get("modified_date"),
                          "tp": l.get("topics", []), "core": bool(l.get("core")), "src": l.get("primary_source"),
                          "h": [[h.get("date"), h.get("text", "")[:160]] for h in l.get("histories", []) if h.get("date")],
                          "a": [[a["key"], a.get("label"), a.get("chapter"), a["text"]] for a in l["articles"]]})
    write_json(out / "search-laws.json", law_index, compact=True)

    # ---- interpretations
    it_index = []
    for r in interps:
        rel = [[x["law_id"], x.get("article"), x["kind"]] for x in r.get("relations", [])]
        it_index.append({"id": r["id"], "no": r["docno"], "d": r.get("date"), "ag": r.get("agency_text") or r.get("historical_name") or "",
                         "agid": r.get("agency_id"), "h": bool(r.get("is_historical")), "cat": r.get("category"),
                         "s": r.get("subject"), "c": r.get("content"), "tp": r.get("topics", []),
                         "v": (r.get("validity") or {}).get("status"), "rel": rel, "fl": r.get("flags", [])})
        write_json(out / "interps" / f"{r['id']}.json", {k: r.get(k) for k in (
            "id", "docno", "date", "date_text", "agency_text", "agency_id", "agency_name", "historical_name", "is_historical",
            "category", "subject", "content", "memo", "sources", "validity", "topics", "flags", "relations", "first_seen",
            "last_synced", "version", "history", "source_missing_since")}, compact=True)
    write_json(out / "search-interps.json", it_index, compact=True)

    # ---- technical
    tech_index = [{"id": t["id"], "t": t["title"], "se": t.get("series"), "is": t.get("issue"), "ag": t.get("agency_id"),
                   "au": t.get("authors"), "d": t.get("date"), "u": t.get("url"), "tp": t.get("topics", []),
                   "isbn": t.get("isbn"), "gpn": t.get("gpn"), "pg": t.get("pages"), "ds": (t.get("dataset") or {}).get("title"),
                   "dsu": (t.get("dataset") or {}).get("url"), "lic": t.get("license"), "ls": t.get("last_synced")} for t in techs]
    write_json(out / "search-tech.json", tech_index, compact=True)

    # ---- sources / status
    status = read_json(paths.META / "source-status.json", {}) or {}
    src_reg = load_yaml(paths.CONFIG / "sources" / "registry.yaml")
    audit = read_json(paths.META / "source-audit-latest.json", {}) or {}
    audit_by = {a["source_id"]: a for a in audit.get("results", [])}
    per_agency: dict[str, dict] = {aid: {"laws": 0, "interps": 0, "tech": 0} for aid in agencies}
    for r in interps:
        if r.get("agency_id") in per_agency:
            per_agency[r["agency_id"]]["interps"] += 1
    for t in techs:
        if t.get("agency_id") in per_agency:
            per_agency[t["agency_id"]]["tech"] += 1
    write_json(out / "sources.json", {
        "registry": src_reg, "status": status, "audit": audit_by, "audit_checked_at": audit.get("checked_at"),
        "agencies": list(agencies.values()), "historical": reg["historical"], "per_agency": per_agency,
        "catalog": read_json(paths.META / "datamoa-catalog.json", None)}, compact=True)

    # ---- update log
    runs = []
    rdir = paths.UPDATES / "runs"
    if rdir.exists():
        for p in sorted(rdir.glob("*.json"), reverse=True)[:60]:
            r = read_json(p)
            for s in r.get("sources", []):
                s["errors"] = [e.splitlines()[0][:300] for e in s.get("errors", [])][:10]
            r["events"] = r.get("events", [])[:200]
            runs.append(r)
    write_json(out / "updates.json", runs, compact=True)

    counts = {"laws": len(laws), "articles": sum(len(l["articles"]) for l in laws), "interps": len(interps),
              "tech": len(techs), "law_versions": sum(1 for _ in (paths.LAWS / "versions").glob("*/*.json")) if (paths.LAWS / "versions").exists() else 0}
    vcount: dict[str, int] = {}
    for r in interps:
        s = (r.get("validity") or {}).get("status")
        vcount[s] = vcount.get(s, 0) + 1
    last_success = {sid: (status.get(sid) or {}).get("last_success") for sid in status}
    latest = runs[0] if runs else None
    manifest = {
        "built_at": now_iso(), "git_sha": os.environ.get("GITHUB_SHA", "")[:12], "counts": counts, "validity_counts": vcount,
        "validity_labels": STATUS_LABELS, "last_success": last_success,
        "last_success_any": max([v for v in last_success.values() if v] or [None], key=lambda x: x or ""),
        "latest_run": {k: latest.get(k) for k in ("run_id", "mode", "started_at", "finished_at", "result")} if latest else None,
        "law_names": law_names,
        "agency_names": {k: v.get("short") or v["name"] for k, v in agencies.items()},
        "topics": load_yaml(paths.CONFIG / "topics" / "topics.yaml"),
        "synonyms": load_yaml(paths.CONFIG / "synonyms" / "search_synonyms.yaml")["groups"],
        "latest": {"interps": [x["id"] for x in it_index[:8]], "tech": [x["id"] for x in tech_index[:6]],
                   "laws": [l["id"] for l in sorted(laws, key=lambda l: l.get("modified_date") or "", reverse=True)[:6]]},
    }
    write_json(out / "manifest.json", manifest, compact=True)
    return {"out": str(out), **counts}


def health(max_age_hours: float) -> tuple[bool, str]:
    status = read_json(paths.META / "source-status.json", {}) or {}
    now = datetime.now(TW)
    bad = []
    for sid in DAILY_SOURCES:
        ls = (status.get(sid) or {}).get("last_success")
        if not ls:
            bad.append(f"{sid}: 從未成功")
            continue
        age = now - datetime.fromisoformat(ls)
        if age > timedelta(hours=max_age_hours):
            bad.append(f"{sid}: 上次成功 {ls}（{age.total_seconds() / 3600:.0f} 小時前）")
    if bad:
        return False, "資料同步逾時：\n" + "\n".join(bad)
    return True, "所有每日來源皆於期限內成功同步"
