"""Fetch small samples from official sources so parsers can be built against real markup.
Respects robots.txt: a URL disallowed for our user agent is recorded, not fetched."""
import io, json, os, sys, time, zipfile, urllib.robotparser
from urllib.parse import urlparse
import requests

UA = "taiwan-agri-land-law-bot/0.1 (+https://github.com/ottoted34/taiwan-agri-land-law)"
OUT = sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/live"
os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers["User-Agent"] = UA
HOSTS = ["law.moj.gov.tw","law.moa.gov.tw","rmis.ardswc.gov.tw","www.afa.gov.tw","www.tari.gov.tw",
 "www.tydares.gov.tw","www.mdares.gov.tw","www.tcdares.gov.tw","www.tndais.gov.tw","www.kdais.gov.tw",
 "www.hdares.gov.tw","www.ttdares.gov.tw","www.tbrs.gov.tw","www.tss.gov.tw","data.moa.gov.tw",
 "data.gov.tw","kmweb.moa.gov.tw","www.moa.gov.tw","www.ardswc.gov.tw","www.ia.gov.tw","www.forest.gov.tw"]
PAGES = {
 "rmis_newslist_p1.html":"https://rmis.ardswc.gov.tw/Web/NewsList.aspx",
 "rmis_newslist_p172.html":"https://rmis.ardswc.gov.tw/Web/NewsList.aspx?page=172",
 "rmis_newsdetail_6075.html":"https://rmis.ardswc.gov.tw/Web/NewsDetail.aspx?id=6075",
 "rmis_newsdetail_100.html":"https://rmis.ardswc.gov.tw/Web/NewsDetail.aspx?id=100",
 "rmis_lawdetail_2013.html":"https://rmis.ardswc.gov.tw/Web/LawDetail.aspx?id=2013",
 "rmis_lawdetail_3008.html":"https://rmis.ardswc.gov.tw/Web/LawDetail.aspx?id=3008",
 "rmis_directory.html":"https://rmis.ardswc.gov.tw/Web/Directory.aspx",
 "rmis_search.html":"https://rmis.ardswc.gov.tw/Web/Search.aspx",
 "moalaw_index.html":"https://law.moa.gov.tw/index.aspx",
 "moa_units.html":"https://www.moa.gov.tw/ws.php?id=2514350",
 "afa_law.html":"https://www.afa.gov.tw/cht/index.php?code=list&ids=353",
 "datamoa_B84.html":"https://data.moa.gov.tw/open_detail.aspx?id=B84",
 "datamoa_740.html":"https://data.moa.gov.tw/open_search.aspx?id=740",
 "datamoa_svc_B84.txt":"https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId=B84",
 "datamoa_svc_740.txt":"https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId=740",
 "datamoa_open.html":"https://data.moa.gov.tw/open.aspx",
 "kdais_techbook.html":"https://www.kdais.gov.tw/ws.php?id=3654",
 "tari_home.html":"https://www.tari.gov.tw/",
}
report = {"ua": UA, "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "robots": {}, "pages": {}}
rps = {}
for h in HOSTS:
    try:
        r = S.get(f"https://{h}/robots.txt", timeout=20)
        txt = r.text if r.status_code == 200 else ""
        open(f"{OUT}/robots_{h}.txt","w",encoding="utf-8").write(f"# status {r.status_code}\n{txt[:20000]}")
        rp = urllib.robotparser.RobotFileParser(); rp.parse(txt.splitlines()); rps[h]=rp
        report["robots"][h] = {"status": r.status_code, "root_allowed": rp.can_fetch(UA, f"https://{h}/")}
    except Exception as e:
        report["robots"][h] = {"error": repr(e)[:300]}
    time.sleep(1)
for name,url in PAGES.items():
    h = urlparse(url).netloc; rp = rps.get(h)
    allowed = rp.can_fetch(UA, url) if rp else None
    entry = {"url": url, "robots_allowed": allowed}
    if allowed is False:
        report["pages"][name] = entry; continue
    try:
        r = S.get(url, timeout=30)
        entry.update(status=r.status_code, ctype=r.headers.get("content-type"), bytes=len(r.content))
        enc = r.apparent_encoding if not r.encoding or r.encoding.lower()=="iso-8859-1" else r.encoding
        open(f"{OUT}/{name}","w",encoding="utf-8").write(r.content.decode(enc or "utf-8", "replace")[:800000])
    except Exception as e:
        entry["error"] = repr(e)[:300]
    report["pages"][name] = entry; time.sleep(1.5)
# MOJ open API (official open data endpoint)
for kind in ["law","order"]:
    url = f"https://law.moj.gov.tw/api/ch/{kind}/json"
    e = {"url": url, "robots_allowed": rps["law.moj.gov.tw"].can_fetch(UA,url) if "law.moj.gov.tw" in rps else None}
    try:
        r = S.get(url, timeout=300); e.update(status=r.status_code, ctype=r.headers.get("content-type"), bytes=len(r.content))
        z = zipfile.ZipFile(io.BytesIO(r.content)); e["files"]=z.namelist()
        raw = z.read(z.namelist()[0]); txt = raw.decode("utf-8-sig")
        d = json.loads(txt); e["top_keys"]=list(d.keys()); laws = d.get("Laws", [])
        e["count"]=len(laws); e["UpdateDate"]=d.get("UpdateDate")
        want = {"申請農業用地作農業設施容許使用審查辦法","農業發展條例","農業用地作農業使用認定及核發證明辦法"}
        keep = [l for l in laws if l.get("LawName") in want]
        json.dump({"UpdateDate": d.get("UpdateDate"), "Laws": keep}, open(f"{OUT}/moj_{kind}_subset.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
        if laws: e["law_keys"]=list(laws[0].keys())
    except Exception as ex:
        e["error"]=repr(ex)[:300]
    report["pages"][f"moj_api_{kind}"]=e
json.dump(report, open(f"{OUT}/_probe_report.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(report, ensure_ascii=False, indent=1))
