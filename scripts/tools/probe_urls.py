"""Fetch an explicit list of URLs (name=url per line in a file) into a folder, honouring robots.txt."""
import sys, os, time, json, urllib.robotparser
from urllib.parse import urlparse
import requests
UA = "taiwan-agri-land-law-bot/0.1 (+https://github.com/ottoted34/taiwan-agri-land-law)"
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
S = requests.Session(); S.headers["User-Agent"] = UA; rps = {}; rep = {}
for line in open(src, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"): continue
    name, url = line.split("=", 1); h = urlparse(url).netloc
    if h not in rps:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = S.get(f"https://{h}/robots.txt", timeout=20); rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except Exception: rp.parse([])
        rps[h] = rp
    if not rps[h].can_fetch(UA, url): rep[name] = "robots_disallowed"; continue
    try:
        r = S.get(url, timeout=60); enc = r.apparent_encoding if (r.encoding or "").lower() in ("", "iso-8859-1") else r.encoding
        open(os.path.join(out, name), "w", encoding="utf-8").write(r.content.decode(enc or "utf-8", "replace")[:1500000])
        rep[name] = {"status": r.status_code, "bytes": len(r.content), "final": r.url}
    except Exception as e: rep[name] = repr(e)[:200]
    time.sleep(1.5)
json.dump(rep, open(os.path.join(out, "_report.json"), "w"), ensure_ascii=False, indent=1); print(json.dumps(rep, ensure_ascii=False, indent=1))
