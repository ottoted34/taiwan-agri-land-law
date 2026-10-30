"""Command line: python -m agrilaw.cli <command>
  sync --mode daily|weekly|technical|monthly|full [--only id,id]
  postprocess
  build             build web/public/data from data/
  check-health      exit 1 if the last successful sync is too old (used by watchdog)"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="agrilaw")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync")
    s.add_argument("--mode", default="daily", choices=["daily", "weekly", "technical", "monthly", "full"])
    s.add_argument("--only", default="")
    sub.add_parser("postprocess")
    dg = sub.add_parser("diagnose")
    dg.add_argument("--out", default="../diagnostics")
    dg.add_argument("--max-pages", type=int, default=0)
    dg.add_argument("--probe", default="", help="space-separated URLs to evaluate instead of the RMIS list check")
    dg.add_argument("--follow", default="", help="regex of same-host links to follow one level when probing")
    sub.add_parser("build")
    h = sub.add_parser("check-health")
    h.add_argument("--max-age-hours", type=float, default=50)
    a = ap.parse_args(argv)
    if a.cmd == "sync":
        from .sync import Run
        log = Run(a.mode, only=[x for x in a.only.split(",") if x] or None).execute()
        print(json.dumps({"result": log["result"], "sources": [{k: x[k] for k in ("source_id", "status", "added", "modified",
              "status_changed", "failed", "rejected")} for x in log["sources"]], "post": log.get("postprocess")},
              ensure_ascii=False, indent=1))
        # exit 0 even on partial failure: the run log records it and the site keeps last good data.
        return 0 if log["result"] != "failed" else 2
    if a.cmd == "diagnose":
        from pathlib import Path
        from .diagnose import probe, rmis_list
        if a.probe:
            print(json.dumps(probe(Path(a.out), a.probe.split(), a.follow), ensure_ascii=False, indent=1))
            return 0
        print(json.dumps(rmis_list(Path(a.out), a.max_pages or None), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "postprocess":
        from .postprocess import postprocess
        print(json.dumps(postprocess(), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "build":
        from .indexing import build
        print(json.dumps(build(), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "check-health":
        from .indexing import health
        ok, msg = health(a.max_age_hours)
        print(msg)
        return 0 if ok else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
