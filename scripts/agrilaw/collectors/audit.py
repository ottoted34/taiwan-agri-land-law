"""Monthly source audit: re-checks every registered source's reachability and robots policy,
so a source that was blocked or offline is automatically re-evaluated instead of being
abandoned forever. It never downloads content from sources that disallow robots."""
from __future__ import annotations

from urllib.parse import urlparse

import requests

from ..http import UA
from ..paths import CONFIG
from ..util import load_yaml, now_iso
from .base import CollectResult, Collector


class SourceAudit(Collector):
    source_id = "source-audit"
    kind = "audit"

    def collect(self, mode: str) -> CollectResult:
        import urllib.robotparser
        res = CollectResult(self.source_id, self.kind)
        reg = load_yaml(CONFIG / "sources" / "registry.yaml")["sources"]
        robots_cache: dict = {}
        for src in reg:
            url = src.get("probe_url") or src.get("url")
            if not url:
                continue
            host = urlparse(url).netloc
            entry = {"source_id": src["id"], "url": url, "checked_at": now_iso()}
            try:
                if host not in robots_cache:
                    rr = self.client.s.get(f"https://{host}/robots.txt", timeout=25)
                    rp = urllib.robotparser.RobotFileParser()
                    if rr.status_code == 200:
                        rp.parse(rr.text.splitlines())
                    else:
                        rp.allow_all = True
                    robots_cache[host] = rp
                allowed = robots_cache[host].can_fetch(UA, url)
                entry["robots_allowed"] = allowed
                if allowed:
                    r = self.client.s.get(url, timeout=30)
                    self.client.requests_made += 1
                    entry["http_status"] = r.status_code
                    entry["reachable"] = r.status_code < 400
                else:
                    entry["reachable"] = None
            except requests.RequestException as e:
                robots_cache.setdefault(host, None)
                entry["reachable"] = False
                entry["error"] = type(e).__name__
            except AttributeError:  # cached None robots (host unreachable)
                entry["reachable"] = False
                entry["error"] = "host unreachable"
            res.records.append(entry)
        res.requests = self.client.requests_made
        return res
