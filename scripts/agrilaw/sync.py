"""Sync orchestrator.
Guarantees:
  * a failed / blocked / malformed source never deletes or overwrites stored records;
  * a complete listing that shrinks abnormally is quarantined, not applied;
  * records missing from a complete listing are flagged, never deleted;
  * every run is logged (data/updates) with added / modified / status-changed / failed counts."""
from __future__ import annotations

import os
import re
import traceback
from collections import Counter

from . import paths
from .agencies import resolve
from .articles import sort_key
from .collectors.agency_letters import ForestLetters, TalisLetters
from .collectors.audit import SourceAudit
from .collectors.base import CollectResult
from .collectors.datamoa import DataMoaPublications
from .collectors.local_glrs import GlrsLocalLaws
from .collectors.moj_law import MojLawCollector
from .collectors.rmis import RmisInterpretations, RmisLawExp, RmisLaws
from .http import Client
from .postprocess import postprocess
from .store import Store, content_hash
from .util import clean, date_in_text, interp_id, load_yaml, nfkc, normalize_docno, now_iso, read_json, sha256, subject_key, write_json, year_hint_from_docno
from .validate import VALIDATORS

SHRINK_RATIO = 0.8

def local_sources() -> list[str]:
    """縣市地方規定來源（config/local/counties.yaml 中 auto_sync=true 者）。"""
    return [c["source_id"] for c in counties() if c.get("auto_sync") and c.get("source_id")]


def counties() -> list[dict]:
    p = paths.CONFIG / "local" / "counties.yaml"
    return (load_yaml(p) or {}).get("counties", []) if p.exists() else []


AGENCY_LETTERS = ["forest-interpretations", "talis-green-energy"]

PLANS = {
    "daily": ["moj-law-api", "rmis-laws", "rmis-interpretations", *AGENCY_LETTERS, *local_sources()],
    "weekly": ["moj-law-api", "rmis-laws", "rmis-interpretations", "rmis-lawexp", *AGENCY_LETTERS, *local_sources()],
    "technical": ["datamoa-publications"],
    "monthly": ["source-audit", "datamoa-publications", "rmis-interpretations", "rmis-laws", "rmis-lawexp", *AGENCY_LETTERS, *local_sources()],
    "full": ["moj-law-api", "rmis-laws", "rmis-interpretations", "rmis-lawexp", "datamoa-publications", "source-audit", *AGENCY_LETTERS, *local_sources()],
}


class Run:
    def __init__(self, mode: str, client: Client | None = None, only: list[str] | None = None):
        self.mode = mode
        self.client = client or Client()
        self.only = only
        self.started = now_iso()
        self.run_id = os.environ.get("GITHUB_RUN_ID") or self.started.replace(":", "").replace("+", "p")
        self.log: dict = {"run_id": self.run_id, "mode": mode, "started_at": self.started, "sources": [],
                          "events": [], "deploy": os.environ.get("DEPLOY_RESULT", "pending")}
        self.laws = Store(paths.LAWS)
        self.interps = Store(paths.INTERP)
        self.tech = Store(paths.TECH)
        self.index = read_json(paths.META / "source-index.json", {}) or {}
        self.status = read_json(paths.META / "source-status.json", {}) or {}

    # ------------------------------------------------------------------ entry
    def execute(self) -> dict:
        plan = self.only or PLANS[self.mode]
        for sid in plan:
            try:
                self.run_source(sid)
            except Exception as e:  # noqa: BLE001 - isolate any source failure
                self.record_source(sid, CollectResult(sid, "?", status="failed", complete=False,
                                                      errors=[f"{type(e).__name__}: {e}", traceback.format_exc()[-1500:]]),
                                   Counter())
        try:
            post = postprocess()
            self.log["postprocess"] = post
        except Exception as e:  # noqa: BLE001
            self.log["postprocess"] = {"error": f"{type(e).__name__}: {e}"}
        self.log["finished_at"] = now_iso()
        self.log["result"] = self.overall()
        write_json(paths.META / "source-index.json", self.index)
        write_json(paths.META / "source-status.json", self.status)
        write_json(paths.UPDATES / "runs" / f"{self.log['started_at'][:10]}_{self.run_id}.json", self.log)
        self.append_summary()
        return self.log

    def overall(self) -> str:
        sts = [s["status"] for s in self.log["sources"]]
        if not sts:
            return "no_sources"
        if all(s in ("ok",) for s in sts):
            changed = sum(s["added"] + s["modified"] + s["status_changed"] for s in self.log["sources"])
            return "success_changed" if changed else "success_no_change"
        if any(s == "ok" or s == "partial" for s in sts):
            return "partial_failure"
        return "failed"

    def append_summary(self) -> None:
        line = {k: self.log[k] for k in ("run_id", "mode", "started_at", "finished_at", "result")}
        line["sources"] = {s["source_id"]: {k: s[k] for k in ("status", "added", "modified", "status_changed", "failed")}
                           for s in self.log["sources"]}
        p = paths.UPDATES / "log.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        import json
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------ per source
    def run_source(self, sid: str) -> None:
        cfg: dict = {}
        if sid == "rmis-interpretations":
            cfg["_known"] = {k: {"list_hash": v.get("list_hash")} for k, v in self.index.items() if k.startswith("rmis:")}
            cfg["daily_pages"] = 3
            col = RmisInterpretations(cfg, self.client)
        elif sid == "moj-law-api":
            col = MojLawCollector(cfg, self.client)
        elif sid == "rmis-laws":
            known = set()
            vdir = paths.LAWS / "versions"
            if vdir.exists():
                for p in vdir.glob("*/*.json"):
                    m = re.match(r"rmis-h(\d+)", p.stem)
                    if m:
                        known.add(int(m.group(1)))
            cfg["_known_history_ids"] = sorted(known)
            col = RmisLaws(cfg, self.client)
        elif sid == "rmis-lawexp":
            cfg["_laws"] = [{"law_id": l["id"], "lawexp_url": l["rmis"]["lawexp_url"]}
                            for l in self.laws.all() if (l.get("rmis") or {}).get("lawexp_url")]
            col = RmisLawExp(cfg, self.client)
        elif sid == "datamoa-publications":
            col = DataMoaPublications(cfg, self.client)
        elif sid == "source-audit":
            col = SourceAudit(cfg, self.client)
        elif sid in AGENCY_LETTERS:
            prefix = "forest:" if sid == "forest-interpretations" else "talis:"
            cfg["_known"] = [k for k in self.index if k.startswith(prefix)]
            col = (ForestLetters if sid == "forest-interpretations" else TalisLetters)(cfg, self.client)
        elif sid.startswith("local-"):
            county = next((c for c in counties() if c.get("source_id") == sid), None)
            if county is None:
                raise ValueError(f"{sid} 未在 config/local/counties.yaml 設定")
            col = GlrsLocalLaws({"county": county}, self.client)
        else:
            raise ValueError(sid)
        before = self.client.requests_made
        res = col.collect(self.mode)
        res.requests = self.client.requests_made - before
        stats = Counter()
        if res.status in ("failed", "robots_disallowed", "unavailable") or (not res.records and res.errors):
            self.record_source(sid, res, stats)
            return
        if sid == "rmis-interpretations":
            self.apply_interpretations(res, stats)
        elif sid == "moj-law-api":
            self.apply_laws_moj(res, stats)
        elif sid == "rmis-laws":
            self.apply_laws_rmis(res, stats)
        elif sid == "rmis-lawexp":
            self.apply_lawexp(res, stats)
        elif sid == "datamoa-publications":
            self.apply_technical(res, stats)
        elif sid == "source-audit":
            write_json(paths.META / "source-audit-latest.json", {"checked_at": now_iso(), "results": res.records})
        elif sid in AGENCY_LETTERS:
            self.apply_agency_letters(res, stats)
        elif sid.startswith("local-"):
            self.apply_local_laws(res, stats, col.county)
        self.record_source(sid, res, stats)

    def record_source(self, sid: str, res: CollectResult, stats: Counter) -> None:
        status = res.status
        if stats.get("quarantined"):
            status = "quarantined"
        entry = {"source_id": sid, "status": status, "complete": res.complete, "added": stats["added"],
                 "modified": stats["modified"], "status_changed": stats["status_changed"],
                 "unchanged": stats["unchanged"], "rejected": stats["rejected"], "failed": len(res.errors),
                 "missing_flagged": stats["missing"], "requests": res.requests, "notes": res.notes[:30],
                 "errors": [e[:500] for e in res.errors[:30]]}
        self.log["sources"].append(entry)
        st = self.status.setdefault(sid, {})
        st["last_checked"] = now_iso()
        st["last_status"] = status
        st["last_errors"] = entry["errors"][:5]
        if status in ("ok", "partial"):
            st["last_success"] = now_iso()
            if res.complete:
                st["last_full_compare"] = now_iso()
            if stats["added"] or stats["modified"] or stats["status_changed"]:
                st["last_changed"] = now_iso()

    def event(self, kind: str, **kw) -> None:
        if len(self.log["events"]) < 2000:
            self.log["events"].append({"kind": kind, **kw})

    def quarantine(self, sid: str, res: CollectResult, reason: str, stats: Counter) -> None:
        write_json(paths.QUARANTINE / sid / f"{self.run_id}.json",
                   {"reason": reason, "at": now_iso(), "records": res.records[:5000], "notes": res.notes})
        res.errors.append("已隔離：" + reason)
        stats["quarantined"] += 1
        self.event("quarantine", source=sid, reason=reason)

    # ------------------------------------------------------------------ interpretations
    def apply_interpretations(self, res: CollectResult, stats: Counter) -> None:
        known_keys = [k for k in self.index if k.startswith("rmis:")]
        listed = res.extra.get("listed_keys", [])
        if res.extra.get("full_crawl") and known_keys and len(listed) < SHRINK_RATIO * len(known_keys):
            self.quarantine(res.source_id, res, f"完整列表僅 {len(listed)} 筆，少於既有 {len(known_keys)} 筆之 {int(SHRINK_RATIO*100)}%", stats)
            return
        for raw in res.records:
            if not raw.get("docno") or "字第" not in raw["docno"]:
                raw["docno"] = clean(raw.get("docno_text") or raw.get("docno") or "")
                raw.setdefault("flags_in", []).append("docno_unparsed")
            errs = VALIDATORS["interpretation"](raw)
            if errs:
                stats["rejected"] += 1
                res.errors.append(f"{raw['source_key']} 驗證失敗：{'；'.join(errs)}")
                continue
            self.upsert_interpretation(raw, stats)
        if res.complete and listed:
            listed_set = set(listed)
            for sk in known_keys:
                if sk not in listed_set:
                    rid = self.index[sk]["id"]
                    r = self.interps.get(rid)
                    if r and not r.get("source_missing_since"):
                        r["source_missing_since"] = now_iso()
                        self.interps.put(r)
                        stats["missing"] += 1
                        self.event("missing_from_source", id=rid, source_key=sk)

    FIELDS = ("docno", "date", "date_text", "agency_text", "category", "subject", "content", "memo")

    def upsert_interpretation(self, raw: dict, stats: Counter) -> str:
        """Identity = 發文字號 + 發文日期 + 主旨. A compiled ruling set can carry several different
        items under one 字號 and date, so 字號+日期 alone must never merge documents."""
        sk = raw["source_key"]
        rid = interp_id(raw["docno"], raw.get("date"), raw.get("subject", ""))
        mapped = (self.index.get(sk) or {}).get("id")
        if mapped and mapped != rid:
            old = self.interps.get(mapped)
            other_primary = [x for x in (old or {}).get("sources", []) if x.get("source_key") != sk and str(x.get("source_key", "")).startswith("rmis:")]
            if old and (not other_primary or not sk.startswith("rmis:")) and (sk.startswith("rmis:") or len(old.get("sources", [])) <= 1):
                # the stored record belongs only to this source key: its identity changed (official edit)
                rid_keep = mapped
            else:
                rid_keep = rid  # mapping pointed at another document (old collision): detach
                if old:
                    old["sources"] = [s for s in old["sources"] if s.get("source_key") != sk] or old["sources"]
                    self.interps.put(old)
                self.event("identity_split", source_key=sk, from_id=mapped, to_id=rid)
            rid = rid_keep
        existing = self.interps.get(rid)
        ag = resolve(raw.get("agency_text", ""), raw.get("date"), raw.get("docno", ""))
        src = {**raw["source"], "source_key": sk}
        flags_in = raw.get("flags_in", [])
        if existing is None:
            rec = {"id": rid, "doc_class": "interpretation", **{k: raw.get(k, "") for k in self.FIELDS}, **ag,
                   "year_hint": year_hint_from_docno(raw["docno"]) if not raw.get("date") else None,
                   "sources": [src], "first_seen": now_iso(), "last_synced": now_iso(), "version": 1, "flags_in": flags_in,
                   "validity": {"status": "no_known_cessation", "basis": [], "confirmed": False}}
            rec["content_hash"] = content_hash("interpretation", rec)
            self.interps.put(rec)
            stats["added"] += 1
            self.event("added", type="interpretation", id=rid, docno=raw["docno"], date=raw.get("date"))
        else:
            new = dict(existing)
            primary = raw["source"]["source_id"] == "rmis-interpretations" or existing["sources"][0].get("source_key") == sk
            if primary:  # list/detail system is authoritative; law-exp copies only add a source
                new.update({k: raw.get(k, "") for k in self.FIELDS if raw.get(k) or k in ("memo",)})
                new.update(ag)
                new["year_hint"] = year_hint_from_docno(raw["docno"]) if not new.get("date") else None
            new["sources"] = [s for s in existing.get("sources", []) if s.get("source_key") != sk] + [src]
            new["last_synced"] = now_iso()
            new["flags_in"] = sorted(set(existing.get("flags_in", [])) | set(flags_in)) if not primary else flags_in
            new.pop("source_missing_since", None)
            h = content_hash("interpretation", new)
            if h != existing.get("content_hash"):
                hist = existing.get("history", [])
                hist.append({"at": now_iso(), "previous_hash": existing.get("content_hash"),
                             "changed_fields": [k for k in ("subject", "content", "category", "docno", "date") if existing.get(k) != new.get(k)],
                             "previous": {k: existing.get(k) for k in ("subject", "content", "category", "date") if existing.get(k) != new.get(k)}})
                new["history"] = hist[-10:]
                new["content_hash"] = h
                new["version"] = existing.get("version", 1) + 1
                stats["modified"] += 1
                self.event("modified", type="interpretation", id=rid, docno=raw["docno"])
            else:
                stats["unchanged"] += 1
            self.interps.put(new)
        self.index[sk] = {"id": rid, "list_hash": raw.get("list_hash")}
        return rid

    # ------------------------------------------------------------------ laws
    def _save_law(self, rec: dict, stats: Counter, source_label: str) -> None:
        rec["articles"] = sorted(rec["articles"], key=lambda a: sort_key(a["key"].lstrip("P")))
        existing = self.laws.get(rec["id"])
        rec["content_hash"] = content_hash("law", rec)
        rec["last_checked"] = now_iso()
        if existing is None:
            rec["first_seen"] = now_iso()
            rec["last_changed"] = now_iso()
            self.laws.put(rec)
            self.snapshot(rec, source_label)
            stats["added"] += 1
            self.event("added", type="law", id=rec["id"], name=rec["name"])
            return
        keep = {k: existing[k] for k in ("first_seen", "rmis", "former_names", "moj") if k in existing}
        merged = {**existing, **rec, **{k: v for k, v in keep.items() if k not in rec}}
        if merged["content_hash"] != existing.get("content_hash"):
            merged["last_changed"] = now_iso()
            changed = sorted({a["key"] for a in merged["articles"]} ^ {a["key"] for a in existing.get("articles", [])} |
                             {a["key"] for a in merged["articles"] for b in existing.get("articles", [])
                              if a["key"] == b["key"] and a["text"] != b["text"]}, key=lambda k: sort_key(k.lstrip("P")))
            merged.setdefault("change_log", []).append({"at": now_iso(), "from_modified": existing.get("modified_date"),
                                                        "to_modified": merged.get("modified_date"), "articles": changed[:200]})
            merged["change_log"] = merged["change_log"][-20:]
            self.laws.put(merged)
            self.snapshot(merged, source_label)
            stats["modified"] += 1
            if existing.get("status") != merged.get("status"):
                stats["status_changed"] += 1
            self.event("law_amended", id=merged["id"], name=merged["name"], articles=changed[:50],
                       modified_date=merged.get("modified_date"))
        else:
            existing["last_checked"] = now_iso()
            for k in ("rmis", "moj"):
                if k in rec:
                    existing[k] = rec[k]
            self.laws.put(existing)
            stats["unchanged"] += 1

    def snapshot(self, law: dict, source_label: str) -> None:
        vid = f"{law.get('modified_date') or 'undated'}-{law['content_hash'][:8]}"
        p = paths.LAWS / "versions" / law["id"] / f"{vid}.json"
        if not p.exists():
            write_json(p, {"law_id": law["id"], "version_id": vid, "name": law["name"],
                           "modified_date": law.get("modified_date"), "kind": "captured", "captured_at": now_iso(),
                           "source": source_label, "articles": law["articles"], "is_full_text": True,
                           "note": "本系統擷取時之現行條文快照"})

    def migrate_law_id(self, old_id: str, new_id: str) -> None:
        """A law first stored from RMIS (e.g. MOJ was down) gets its national PCode once MOJ data arrives."""
        import shutil
        old = self.laws.get(old_id)
        if not old:
            return
        src_dir, dst_dir = paths.LAWS / "versions" / old_id, paths.LAWS / "versions" / new_id
        if src_dir.exists():
            dst_dir.mkdir(parents=True, exist_ok=True)
            for f in src_dir.glob("*.json"):
                d = read_json(f)
                d["law_id"] = new_id
                if not (dst_dir / f.name).exists():
                    write_json(dst_dir / f.name, d)
            shutil.rmtree(src_dir)
        self.laws.path(old_id).unlink(missing_ok=True)
        off = read_json(paths.RELATIONS / "official.json", None)
        if off:
            for r in off.get("relations", []):
                if r["law_id"] == old_id:
                    r["law_id"] = new_id
            write_json(paths.RELATIONS / "official.json", off)
        self.event("law_id_migrated", old_id=old_id, new_id=new_id, name=old.get("name"))

    def apply_laws_moj(self, res: CollectResult, stats: Counter) -> None:
        provisional = {l["name"]: l for l in self.laws.all() if l.get("primary_source") == "rmis-laws" and l["id"].startswith("RMIS-")}
        for raw in res.records:
            errs = VALIDATORS["law"](raw)
            if errs:
                stats["rejected"] += 1
                res.errors.append(f"{raw.get('name')} 驗證失敗：{'；'.join(errs)}")
                continue
            rec = {**raw, "doc_class": "law", "sources": [raw.pop("source")]}
            rec["primary_source"] = "moj-law-api"
            rec["former_names"] = sorted(set(re.findall(r"原名稱[：:]\s*([^；;，,）)]+)", " ".join(h["text"] for h in rec["histories"]))))
            prov = provisional.get(rec["name"])
            if prov and prov["id"] != rec["id"]:
                rec["rmis"] = prov.get("rmis")
                self.migrate_law_id(prov["id"], rec["id"])
            self._save_law(rec, stats, "全國法規資料庫")

    def apply_laws_rmis(self, res: CollectResult, stats: Counter) -> None:
        by_name = {l["name"]: l for l in self.laws.all()}
        for raw in res.records:
            name = raw["name"]
            moj = by_name.get(name)
            rmis_meta = {"rmis_law_id": raw["rmis_law_id"], "url": raw["source"]["url"], "lawexp_url": raw["lawexp_url"],
                         "histories": raw["histories"], "attachments": raw["attachments"],
                         "modified_date": raw["modified_date"], "fetched_at": raw["source"]["fetched_at"]}
            if moj and moj.get("primary_source") == "moj-law-api":
                # MOJ is authoritative for 法律/命令; RMIS adds relations, histories and cross-check
                moj["rmis"] = rmis_meta
                rm = {a["key"]: a["text"] for a in raw["articles"]}
                diffs = [a["key"] for a in moj["articles"] if a["key"] in rm and re.sub(r"\s", "", rm[a["key"]]) != re.sub(r"[\s]", "", a["text"]) ]
                moj["cross_check"] = {"source": "rmis-laws", "at": now_iso(), "rmis_modified": raw["modified_date"],
                                      "moj_modified": moj.get("modified_date"), "article_count_rmis": len(raw["articles"]),
                                      "article_count_moj": len(moj["articles"]), "text_differs": diffs[:50]}
                if raw["modified_date"] and moj.get("modified_date") and raw["modified_date"] > moj["modified_date"]:
                    moj.setdefault("flags", [])
                    if "rmis_newer" not in moj["flags"]:
                        moj["flags"].append("rmis_newer")
                self.laws.put(moj)
                law_id = moj["id"]
                stats["unchanged"] += 1
            else:
                errs = VALIDATORS["law"]({**raw, "source": raw["source"]})
                if errs:
                    stats["rejected"] += 1
                    res.errors.append(f"{name} 驗證失敗：{'；'.join(errs)}")
                    continue
                law_id = moj["id"] if moj else f"RMIS-{raw['rmis_law_id']}"
                rec = {"id": law_id, "name": name, "level": raw["level"], "category": "農業部農村發展及水土保持署（RMIS）",
                       "official_url": raw["source"]["url"], "modified_date": raw["modified_date"], "effective_date": None,
                       "effective_note": "", "abandon_note": "", "status": "current",
                       "histories": [{"seq": i + 1, "text": h["text"], "date": h["date"]} for i, h in enumerate(reversed(raw["histories"]))],
                       "articles": raw["articles"], "attachments": raw["attachments"], "doc_class": "law",
                       "sources": [raw["source"]], "primary_source": "rmis-laws", "rmis": rmis_meta,
                       "topics": ["facility"] if "容許" in name else (["land_control"] if "變更" in name else []),
                       "docno_text": raw["docno_text"]}
                self._save_law(rec, stats, "農地及農舍法規檢索系統")
            for v in raw.get("versions", []):
                vid = f"rmis-h{v['rmis_history_id']}"
                p = paths.LAWS / "versions" / law_id / f"{vid}.json"
                if not p.exists():
                    write_json(p, {"law_id": law_id, "version_id": vid, "name": v["name"], "modified_date": v["date"],
                                   "kind": "official_history", "entry": v["entry"], "docno_text": v["docno_text"],
                                   "url": v["url"], "is_full_text": v["is_full_text"], "articles": v["articles"],
                                   "content": v["content"] if not v["is_full_text"] else "", "captured_at": now_iso()})
                    self.event("history_version", law_id=law_id, version=vid)

    def apply_lawexp(self, res: CollectResult, stats: Counter) -> None:
        if len(res.records) < 10:
            self.quarantine(res.source_id, res, f"法規對應函釋僅取得 {len(res.records)} 筆，疑似異常", stats)
            return
        by_docno: dict[str, list[dict]] = {}
        for r in self.interps.all():
            by_docno.setdefault(r["docno"], []).append(r)
        rels, created = [], 0
        for it in res.records:
            docno = it["docno"]
            cands = by_docno.get(docno, [])
            tk = subject_key(it["title"])
            match = next((c for c in cands if subject_key(c.get("subject")) == tk), None)
            if match is None and cands and len(cands) == 1 and not tk:
                match = cands[0]
            if match is None:
                match = next((c for c in cands if tk and (tk[:20] in subject_key(c.get("subject")) or subject_key(c.get("subject"))[:20] in tk)), None)
            sk = f"rmis-lawexp:{docno}|{tk[:30]}"
            if match is None:
                dtx = date_in_text(it.get("docno_text", ""))
                raw = {"source_key": sk, "docno": docno, "date": dtx, "date_text": it.get("docno_text", "") if dtx else "", "agency_text": "", "category": "",
                       "subject": it["title"], "content": it["content"], "memo": "",
                       "source": {"source_id": "rmis-lawexp", "url": it["evidence_url"], "fetched_at": now_iso()}}
                if "字第" not in docno:
                    raw["flags_in"] = ["docno_unparsed"]
                if VALIDATORS["interpretation"](raw):
                    stats["rejected"] += 1
                    continue
                rid = self.upsert_interpretation(raw, stats)
                rec = self.interps.get(rid)
                by_docno.setdefault(docno, []).append(rec)
                created += 1
            else:
                rid = match["id"]
                if not any(s.get("source_key") == sk for s in match.get("sources", [])):
                    match["sources"] = match.get("sources", []) + [{"source_id": "rmis-lawexp", "url": it["evidence_url"],
                                                                    "fetched_at": now_iso(), "source_key": sk}]
                    self.interps.put(match)
                self.index[sk] = {"id": rid}
            rels.append({"interp_id": rid, "law_id": it["law_id"], "article": None, "kind": "official", "evidence": it["evidence_url"]})
        uniq = {(r["interp_id"], r["law_id"]): r for r in rels}
        rels = list(uniq.values())
        old = read_json(paths.RELATIONS / "official.json", {}) or {}
        if sha256(sorted((r["interp_id"], r["law_id"]) for r in rels)) != sha256(sorted((r["interp_id"], r["law_id"]) for r in old.get("relations", []))):
            stats["status_changed"] += 0
        write_json(paths.RELATIONS / "official.json", {"generated_at": now_iso(), "relations": rels})
        res.notes.append(f"官方列示關聯 {len(rels)} 筆；本次新收錄僅見於法規對應頁之函釋 {created} 筆（官方頁面未載發文日期）")

    # ------------------------------------------------------------------ other agencies' letter pages
    def apply_agency_letters(self, res: CollectResult, stats: Counter) -> None:
        """同一函釋已由其他來源（多為 RMIS）收錄時（字號＋日期相同），只加註來源，不覆寫內容；
        否則以本來源為主新增。完整列表中消失者標示 source_missing，不刪除。"""
        prefix = res.source_id.split("-")[0] + ":"
        by_key: dict[tuple, list[dict]] = {}
        for r in self.interps.all():
            by_key.setdefault((r["docno"], r.get("date")), []).append(r)
        merged = 0
        for raw in res.records:
            sk = raw["source_key"]
            if "字第" not in (raw.get("docno") or ""):
                raw.setdefault("flags_in", []).append("docno_unparsed")
            errs = VALIDATORS["interpretation"](raw)
            if errs:
                stats["rejected"] += 1
                res.errors.append(f"{sk} 驗證失敗：{'；'.join(errs)}")
                continue
            mapped = (self.index.get(sk) or {}).get("id")
            cands = by_key.get((raw["docno"], raw.get("date")), [])
            other = [c for c in cands if not any(s.get("source_key") == sk for s in c.get("sources", []))
                     and c["sources"] and c["sources"][0].get("source_key") != sk]
            if not mapped and len(other) == 1:
                rec = other[0]
                rec["sources"] = rec.get("sources", []) + [{**raw["source"], "source_key": sk}]
                rec["last_synced"] = now_iso()
                self.interps.put(rec)
                self.index[sk] = {"id": rec["id"], "list_hash": raw.get("list_hash")}
                stats["unchanged"] += 1
                merged += 1
                continue
            if mapped:
                existing = self.interps.get(mapped)
                if existing and existing["sources"][0].get("source_key") != sk:  # merged into another source's record
                    stats["unchanged"] += 1
                    continue
            rid = self.upsert_interpretation(raw, stats)
            rec = self.interps.get(rid)
            by_key.setdefault((rec["docno"], rec.get("date")), []).append(rec)
        listed = res.extra.get("listed_keys", [])
        if res.complete and listed:
            known = [k for k in self.index if k.startswith(prefix)]
            if len(listed) < SHRINK_RATIO * len(known):
                self.quarantine(res.source_id, res, f"完整列表僅 {len(listed)} 筆，少於既有 {len(known)} 筆之 {int(SHRINK_RATIO*100)}%", stats)
                return
            ls = set(listed)
            for sk in known:
                if sk not in ls:
                    r = self.interps.get(self.index[sk]["id"])
                    if r and r["sources"][0].get("source_key") == sk and not r.get("source_missing_since"):
                        r["source_missing_since"] = now_iso()
                        self.interps.put(r)
                        stats["missing"] += 1
        res.notes.append(f"與既有函釋（字號＋日期相同）合併為同一筆並加註來源：{merged} 筆")

    # ------------------------------------------------------------------ local (county) laws
    def apply_local_laws(self, res: CollectResult, stats: Counter, county: dict) -> None:
        """地方規定只收錄 counties.yaml 審核列入者；官方頁面解析結果經驗證才寫入，失敗時保留舊資料。"""
        for raw in res.records:
            errs = VALIDATORS["law"](raw)
            if errs:
                stats["rejected"] += 1
                res.errors.append(f"{raw.get('name')} 驗證失敗：{'；'.join(errs)}")
                continue
            item = raw["config"]
            rec = {"id": f"{county['code']}-{raw['law_system_id']}", "name": raw["name"], "level": raw["level"],
                   "category": f"{county['name']}／{raw['system_path']}", "official_url": raw["source"]["url"],
                   "modified_date": raw["modified_date"], "published_date": raw["published_date"], "effective_date": None,
                   "effective_note": "地方法規系統未提供施行日期欄位，施行日期以發布令或條文所定為準",
                   "abandon_note": raw.get("status_note", ""), "status": raw["status"], "docno_text": raw["docno_text"],
                   "system_path": raw["system_path"], "county": county["name"],
                   "histories": [{"seq": i + 1, "text": h["text"], "date": h["date"]} for i, h in enumerate(raw.get("histories", []))],
                   "articles": raw["articles"], "attachments": raw["attachments"], "foreword": raw.get("foreword", ""),
                   "doc_class": "law", "sources": [raw["source"]], "primary_source": res.source_id,
                   "topics": item.get("topics", []), "scenarios": item.get("scenarios", []), "core": False,
                   "review": {k: item.get(k) for k in ("reviewed_by", "reviewed_at", "basis", "issue") if item.get(k)}}
            self._save_law(rec, stats, f"{county['name']}法規查詢系統")
        cands = read_json(paths.META / "local-candidates.json", {}) or {}
        cands[county["name"]] = {"checked_at": now_iso(), "source_id": res.source_id, "candidates": res.extra.get("candidates", [])}
        write_json(paths.META / "local-candidates.json", cands)
        if res.extra.get("candidates"):
            res.notes.append(f"{county['name']}有 {len(res.extra['candidates'])} 筆待管理者審核之候選法規（data/metadata/local-candidates.json）")

    # ------------------------------------------------------------------ technical
    def apply_technical(self, res: CollectResult, stats: Counter) -> None:
        seen_ids = set()
        for raw in res.records:
            errs = VALIDATORS["technical"](raw)
            if errs:
                stats["rejected"] += 1
                continue
            rid = "tech-" + sha256(raw["source_key"])[:12]
            if rid in seen_ids:
                stats["unchanged"] += 1  # exact duplicate row inside the official dataset
                continue
            seen_ids.add(rid)
            existing = self.tech.get(rid)
            rec = {"id": rid, **{k: v for k, v in raw.items() if k not in ("source",)}, "sources": [raw["source"]]}
            rec["content_hash"] = content_hash("technical", rec)
            rec["last_synced"] = now_iso()
            if existing is None:
                rec["first_seen"] = now_iso()
                self.tech.put(rec)
                stats["added"] += 1
            elif existing.get("content_hash") != rec["content_hash"]:
                rec["first_seen"] = existing.get("first_seen")
                rec["version"] = existing.get("version", 1) + 1
                self.tech.put(rec)
                stats["modified"] += 1
            else:
                existing["last_synced"] = now_iso()
                existing.pop("source_missing_since", None)
                self.tech.put(existing)
                stats["unchanged"] += 1
        complete = set(getattr(res, "extra", {}).get("complete_units", []))
        for t in self.tech.all():
            if (t.get("dataset") or {}).get("unit_id") in complete and t["id"] not in seen_ids and not t.get("source_missing_since"):
                t["source_missing_since"] = now_iso()
                self.tech.put(t)
                stats["missing"] += 1
