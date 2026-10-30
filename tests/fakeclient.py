"""Offline HTTP client serving recorded official pages, with switches to simulate failures."""
import json
import re
from pathlib import Path

from agrilaw.http import BadContent, Client, Response, SourceUnavailable

FIX = Path(__file__).resolve().parent / "fixtures"


class FakeClient(Client):
    def __init__(self, routes=None, down=(), mutate=None):
        super().__init__(min_interval=0, retries=0)
        self.routes = routes if routes is not None else default_routes()
        self.down = set(down)      # host substrings that are "offline"
        self.mutate = mutate or {}  # url -> callable(text)->text
        self.calls = []

    def robots_allowed(self, url):
        return True

    def get(self, url, timeout=None, expect_html=False):
        self.calls.append(url)
        self.requests_made += 1
        if any(h in url for h in self.down):
            raise SourceUnavailable(f"simulated outage {url}")
        body = None
        for pat, val in self.routes.items():
            if re.fullmatch(pat, url):
                body = val(url) if callable(val) else val
                break
        if body is None:
            raise SourceUnavailable(f"HTTP 404 {url}")
        if url in self.mutate:
            body = self.mutate[url](body if isinstance(body, str) else body.decode("utf-8"))
        raw = body.encode("utf-8") if isinstance(body, str) else body
        text = raw.decode("utf-8", "replace") if expect_html else ""
        if expect_html and "<html" not in text[:5000].lower():
            raise BadContent(url)
        return Response(url, 200, raw, {}, text)


def _read(rel):
    return (FIX / rel).read_text(encoding="utf-8")


def moj_zip(kind):
    import io
    import zipfile
    data = json.loads(_read(f"live/moj_{kind}_subset.json"))
    # pad to look like the national database (the collector rejects tiny datasets)
    data["Laws"] += [{"LawName": f"填充法規{i}", "LawURL": "", "LawArticles": []} for i in range(150)]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("ChLaw.json" if kind == "law" else "ChOrder.json", json.dumps(data, ensure_ascii=False))
    return buf.getvalue()


def default_routes():
    B = r"https://rmis\.ardswc\.gov\.tw/Web/"
    p1 = _read("live/rmis_newslist_p1.html").replace("page=172", "page=5")  # shrink the site to 5 pages
    pl = _read("live/rmis_newslist_p172.html")
    p50 = _read("live2/rmis_newslist_p50.html")
    det = {"6075": _read("live/rmis_newsdetail_6075.html"), "6069": _read("live2/rmis_newsdetail_6069.html")}
    return {
        r"https://law\.moj\.gov\.tw/api/ch/law/json": moj_zip("law"),
        r"https://law\.moj\.gov\.tw/api/ch/order/json": moj_zip("order"),
        B + r"NewsList\.aspx": p1,
        B + r"NewsList\.aspx\?page=5": pl,
        B + r"NewsList\.aspx\?page=\d+": p50,
        B + r"NewsDetail\.aspx\?id=(\d+)": lambda u: det.get(u.rsplit("=", 1)[1], _synthetic_detail(u)),
        B + r"Directory\.aspx": _read("live/rmis_directory.html"),
        B + r"LawDetail\.aspx\?id=2013": _read("live/rmis_lawdetail_2013.html"),
        B + r"LawDetail\.aspx\?id=3008": _read("live/rmis_lawdetail_3008.html"),
        B + r"LawDetail\.aspx\?id=1001": _read("live2/rmis_lawdetail_1001.html"),
        B + r"LawHistoryDetail\.aspx\?id=68": _read("live2/rmis_lawhistory_68.html"),
        B + r"LawHistoryDetail\.aspx\?id=211": _read("live2/rmis_lawhistory_211.html"),
        B + r"LawExp\.aspx\?id=2013": _read("live2/rmis_lawexp_2013.html"),
        B + r"LawExp\.aspx\?id=1001": _read("live2/rmis_lawexp_1001.html"),
        r"https://data\.moa\.gov\.tw/Service/OpenData/DataFileService\.aspx\?UnitId=740": _read("live/datamoa_svc_740.txt"),
        r"https://data\.moa\.gov\.tw/Service/OpenData/DataFileService\.aspx\?UnitId=B84": _read("live/datamoa_svc_B84.txt"),
    }


def _synthetic_detail(url):
    """Detail pages we did not record: rebuild from the list-page row so the pipeline can be exercised.
    Used ONLY inside tests; never written to the real data folder."""
    rid = url.rsplit("=", 1)[1]
    for f in ["live/rmis_newslist_p1.html", "live/rmis_newslist_p172.html", "live2/rmis_newslist_p50.html"]:
        t = _read(f)
        m = re.search(rf'lvList_hlkEdit_(\d+)"[^>]*href="NewsDetail\.aspx\?id={rid}">([^<]*)</a>', t)
        if m:
            idx = m.group(1)
            g = lambda k: re.search(rf'{k}_{idx}">([^<]*)', t).group(1).strip()
            tpl = _read("live/rmis_newsdetail_6075.html")
            tpl = re.sub(r'(lblExpDate">)[^<]*', rf"\g<1>{g('lvList_lblExpDate')}", tpl)
            tpl = re.sub(r'(lblExpWord">)[^<]*', rf"\g<1>{g('lvList_lblExpWord')}", tpl)
            tpl = re.sub(r'(lblExpTitle">)[^<]*', lambda _m: _m.group(1) + m.group(2), tpl)
            tpl = re.sub(r'(lblExpContent">).*?(</span>)', lambda _m: _m.group(1) + "（測試用內容）" + m.group(2), tpl, flags=re.S)
            return tpl
    return _read("live/rmis_newslist_p1.html")  # invalid id -> list page, like the real site
