"""Update-mechanism scenarios (spec 19.6): add, modify, no change, outage, malformed data,
mass disappearance, duplicates, mid-run failure, build failure isolation."""
import json

import pytest

from agrilaw import paths
from agrilaw.store import Store
from agrilaw.sync import Run
from agrilaw.util import read_json, write_json
from fakeclient import FakeClient, default_routes


def run(mode, client, only=None):
    return Run(mode, client=client, only=only).execute()


def src(log, sid):
    return next(s for s in log["sources"] if s["source_id"] == sid)


@pytest.fixture
def seeded(data_dir):
    write_json(paths.META / "datamoa-catalog.json", {"datasets": []})
    log = run("weekly", FakeClient())
    return log


def test_initial_import(seeded):
    assert src(seeded, "moj-law-api")["status"] == "ok"
    laws = {l["id"]: l for l in Store(paths.LAWS).all()}
    assert "M0020022" in laws and "M0020001" in laws
    assert any(i.startswith("RMIS-3") for i in laws)  # administrative rule only on RMIS
    assert laws["M0020022"]["rmis"]["lawexp_url"].endswith("id=2013")
    its = list(Store(paths.INTERP).all())
    assert len(its) >= 20
    one = next(r for r in its if r["docno"] == "農保規字第1150230515號")
    assert one["date"] == "2026-07-28" and one["agency_id"] == "ardswc"
    assert one["validity"]["status"] in ("no_known_cessation", "possibly_affected", "needs_review", "amended_by_later")
    assert one["validity"]["confirmed"] is False
    # official law->interpretation relation from RMIS LawExp
    off = read_json(paths.RELATIONS / "official.json")
    assert any(x["interp_id"] == one["id"] and x["law_id"] == "M0020022" for x in off["relations"])
    # history version with full text captured
    assert (paths.LAWS / "versions" / "M0020022" / "rmis-h68.json").exists()


def test_no_change_run(seeded):
    # rmis-laws excluded: the offline fixture set only holds 3 of the 24 RMIS law pages
    log = run("daily", FakeClient(), only=["moj-law-api", "rmis-interpretations"])
    for sid in ("moj-law-api", "rmis-interpretations"):
        s = src(log, sid)
        assert s["status"] == "ok" and s["added"] == 0 and s["modified"] == 0
    assert log["result"] == "success_no_change"


def test_modification_detected_and_history_kept(seeded):
    url = "https://rmis.ardswc.gov.tw/Web/NewsDetail.aspx?id=6075"
    c = FakeClient(mutate={url: lambda t: t.replace("復如說明，請查照。", "復如說明（更正），請查照。"),
                           "https://rmis.ardswc.gov.tw/Web/NewsList.aspx": lambda t: t.replace("復如說明，請查照。", "復如說明（更正），請查照。", 1)})
    log = run("daily", c)
    assert src(log, "rmis-interpretations")["modified"] == 1
    rec = next(r for r in Store(paths.INTERP).all() if r["docno"] == "農保規字第1150230515號")
    assert rec["version"] == 2 and "更正" in rec["subject"]
    assert rec["history"][-1]["previous"]["subject"].endswith("復如說明，請查照。")


def test_new_record_added(seeded):
    def extra(t):
        return t.replace('href="NewsDetail.aspx?id=6075">', 'href="NewsDetail.aspx?id=6075">', 1)
    before = len(Store(paths.INTERP).ids())
    # forget one record from the index so it is treated as new on the source
    idx = read_json(paths.META / "source-index.json")
    rid = idx["rmis:6069"]["id"]
    (paths.INTERP / f"{rid}.json").unlink()
    del idx["rmis:6069"]
    write_json(paths.META / "source-index.json", idx)
    log = run("daily", FakeClient(mutate={"https://rmis.ardswc.gov.tw/Web/NewsList.aspx": extra}))
    assert src(log, "rmis-interpretations")["added"] == 1
    assert len(Store(paths.INTERP).ids()) == before


def test_outage_keeps_data(seeded):
    snapshot = {p.name: p.read_text() for p in paths.INTERP.glob("*.json")}
    log = run("daily", FakeClient(down=["rmis.ardswc.gov.tw", "law.moj.gov.tw", "law.taichung.gov.tw", "forest.gov.tw", "talis.moa.gov.tw"]))
    assert src(log, "rmis-interpretations")["status"] != "ok"
    assert log["result"] == "failed"
    after = {p.name: p.read_text() for p in paths.INTERP.glob("*.json")}
    assert set(after) == set(snapshot)
    status = read_json(paths.META / "source-status.json")
    assert status["rmis-interpretations"]["last_status"] != "ok"
    assert "last_success" in status["rmis-interpretations"]  # previous success preserved


def test_malformed_page_rejected(seeded):
    routes = default_routes()
    routes[r"https://rmis\.ardswc\.gov\.tw/Web/NewsList\.aspx"] = "<html><body>系統維護中</body></html>"
    n = len(Store(paths.INTERP).ids())
    log = run("daily", FakeClient(routes=routes))
    assert src(log, "rmis-interpretations")["status"] == "failed"
    assert len(Store(paths.INTERP).ids()) == n


def test_malformed_moj_rejected(seeded):
    routes = default_routes()
    routes[r"https://law\.moj\.gov\.tw/api/ch/order/json"] = b"not a zip"
    routes[r"https://law\.moj\.gov\.tw/api/ch/law/json"] = b"not a zip"
    before = read_json(paths.LAWS / "M0020022.json")
    log = run("daily", FakeClient(routes=routes), only=["moj-law-api"])
    assert src(log, "moj-law-api")["status"] == "failed"
    assert read_json(paths.LAWS / "M0020022.json")["content_hash"] == before["content_hash"]


def test_mass_disappearance_quarantined(seeded):
    routes = default_routes()
    # weekly crawl: page 1 ok but every other page now returns an empty list
    empty = default_routes()[r"https://rmis\.ardswc\.gov\.tw/Web/NewsList\.aspx\?page=5"]
    import re
    empty = re.sub(r"<tr>\s*<td>\s*<span id=\"ContentPlaceHolder1_ucNewsListOut1_lvList_lblRowNum.*?</tr>", "", empty, flags=re.S)
    routes[r"https://rmis\.ardswc\.gov\.tw/Web/NewsList\.aspx\?page=\d+"] = empty
    routes[r"https://rmis\.ardswc\.gov\.tw/Web/NewsList\.aspx\?page=5"] = empty
    n = len(Store(paths.INTERP).ids())
    log = run("weekly", FakeClient(routes=routes), only=["rmis-interpretations"])
    assert src(log, "rmis-interpretations")["status"] == "quarantined"
    assert len(Store(paths.INTERP).ids()) == n
    assert list((paths.QUARANTINE / "rmis-interpretations").glob("*.json"))
    assert not any(r.get("source_missing_since") for r in Store(paths.INTERP).all())


def test_duplicate_docno_not_duplicated(seeded):
    n = len(Store(paths.INTERP).ids())
    run("monthly", FakeClient(), only=["rmis-interpretations"])  # refetches all details
    assert len(Store(paths.INTERP).ids()) == n
    from agrilaw.util import subject_key
    keys = [(r["docno"], r["date"], subject_key(r["subject"])) for r in Store(paths.INTERP).all()]
    assert len(keys) == len(set(keys))
    sk = [s["source_key"] for r in Store(paths.INTERP).all() for s in r["sources"]]
    assert len(sk) == len(set(sk))  # every official record lives in exactly one canonical record


def test_same_docno_different_subject_kept_apart(seeded):
    """A compiled ruling set can hold several items under one 字號 and date; they must not be merged."""
    from agrilaw.collectors.base import CollectResult
    from agrilaw.util import now_iso
    r = Run("daily", client=FakeClient())
    res = CollectResult("rmis-interpretations", "interpretation", complete=False)
    for i, subj in enumerate(["049 釋農業用地作農業使用證明書之審核應以申請書所載共有持分面積審認案", "027 釋涉及所有權移轉之農業用地分割案"]):
        res.records.append({"source_key": f"rmis:99{i}", "docno": "農企字第0960149506號", "date": "2007-09-07", "date_text": "96/9/7",
                            "agency_text": "行政院農業委員會", "category": "解釋令", "subject": subj, "content": f"內容{i}", "memo": "",
                            "source": {"source_id": "rmis-interpretations", "url": f"https://rmis.ardswc.gov.tw/Web/NewsDetail.aspx?id=99{i}", "fetched_at": now_iso()}})
    from collections import Counter
    st = Counter()
    r.apply_interpretations(res, st)
    assert st["added"] == 2
    same = [x for x in Store(paths.INTERP).all() if x["docno"] == "農企字第0960149506號"]
    assert len(same) == 2


def test_lawexp_only_letters_imported(seeded):
    its = list(Store(paths.INTERP).all())
    lawexp_only = [r for r in its if all(s["source_id"] == "rmis-lawexp" for s in r["sources"])]
    assert lawexp_only, "letters listed only on the official law-exp page should be imported"
    assert not any(r["validity"]["status"] == "possibly_affected" and not r.get("date") for r in lawexp_only)
    assert any("date_unknown" in r["flags"] for r in lawexp_only)


def test_midrun_exception_isolated(seeded, monkeypatch):
    from agrilaw.collectors import rmis
    def boom(*a, **k):
        raise RuntimeError("parser crashed")
    monkeypatch.setattr(rmis, "parse_law_detail", boom)
    log = run("daily", FakeClient())
    assert src(log, "rmis-laws")["status"] == "failed"
    assert src(log, "moj-law-api")["status"] == "ok"
    assert src(log, "rmis-interpretations")["status"] == "ok"
    assert log["result"] == "partial_failure"


def test_law_amendment_snapshot_and_impact(seeded):
    from fakeclient import moj_zip
    import io, zipfile
    raw = moj_zip("order")
    z = zipfile.ZipFile(io.BytesIO(raw))
    data = json.loads(z.read("ChOrder.json"))
    for l in data["Laws"]:
        if l["LawName"] == "申請農業用地作農業設施容許使用審查辦法":
            l["LawModifiedDate"] = "20261101"
            l["LawHistories"] += "\r\n18.中華民國一百十五年十一月一日農業部農農保字第 1150000001 號令修正發布第 29 條條文"
            for a in l["LawArticles"]:
                if a["ArticleNo"] == "第 29 條":
                    a["ArticleContent"] += "（測試修正）"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zz:
        zz.writestr("ChOrder.json", json.dumps(data, ensure_ascii=False))
    routes = default_routes()
    routes[r"https://law\.moj\.gov\.tw/api/ch/order/json"] = buf.getvalue()
    log = run("daily", FakeClient(routes=routes), only=["moj-law-api"])
    assert src(log, "moj-law-api")["modified"] == 1
    law = read_json(paths.LAWS / "M0020022.json")
    assert law["modified_date"] == "2026-11-01" and "29" in law["change_log"][-1]["articles"]
    assert len(list((paths.LAWS / "versions" / "M0020022").glob("2025-12-31-*.json"))) == 1
    assert len(list((paths.LAWS / "versions" / "M0020022").glob("2026-11-01-*.json"))) == 1
    ev = [e for e in log["events"] if e["kind"] == "law_amended"]
    assert ev and ev[0]["articles"] == ["29"]


def test_build_outputs(seeded):
    from agrilaw.indexing import build
    out = build()
    assert out["interps"] > 0 and out["laws"] > 0
    m = read_json(paths.WEB_DATA / "manifest.json")
    assert m["counts"]["interps"] == out["interps"]
    assert m["last_success_any"] and "latest_run" not in m
    assert not (paths.WEB_DATA / "updates.json").exists()  # 更新紀錄不發布到網站
    assert "status" not in read_json(paths.WEB_DATA / "sources.json")
    assert (paths.WEB_DATA / "laws" / "M0020022.json").exists()


def test_health_check(seeded):
    from agrilaw.indexing import health
    ok, _ = health(50)
    assert ok
    st = read_json(paths.META / "source-status.json")
    st["rmis-interpretations"]["last_success"] = "2020-01-01T00:00:00+08:00"
    write_json(paths.META / "source-status.json", st)
    ok, msg = health(50)
    assert not ok and "rmis-interpretations" in msg


def test_intermittent_empty_page_not_complete(seeded):
    """Official server sometimes returns「目前無資料可顯示」for a valid page: retry, then mark incomplete (no missing flags)."""
    import re as _re
    routes = default_routes()
    empty = _re.sub(r"<tr>\s*<td>\s*<span id=\"ContentPlaceHolder1_ucNewsListOut1_lvList_lblRowNum.*?</tr>", "",
                    routes[r"https://rmis\.ardswc\.gov\.tw/Web/NewsList\.aspx\?page=5"], flags=_re.S)
    routes = {r"https://rmis\.ardswc\.gov\.tw/Web/NewsList\.aspx\?page=3": empty, **routes}
    log = run("weekly", FakeClient(routes=routes), only=["rmis-interpretations"])
    s = src(log, "rmis-interpretations")
    assert s["complete"] is False and s["missing_flagged"] == 0
    assert any("重試後仍無資料" in n for n in s["notes"])
