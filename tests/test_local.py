"""地方規定（臺中市）：解析官方頁面、同步、失敗保留舊資料、縣市選單資料。"""
from agrilaw import paths
from agrilaw.collectors.local_glrs import parse_glrs_history, parse_glrs_law
from agrilaw.store import Store
from agrilaw.sync import Run, counties
from agrilaw.util import read_json
from fakeclient import FakeClient

URL = "https://law.taichung.gov.tw/LawContent.aspx?id="


def test_parse_points_rule(fixtures):
    r = parse_glrs_law((fixtures / "local/taichung_lawcontent_GL000357.html").read_text(encoding="utf-8"), URL + "GL000357")
    assert r["name"] == "臺中市申請農業用地作農業設施容許使用審查要點"
    assert r["level"] == "行政規則" and r["modified_date"] == "2024-02-21" and r["published_date"] == "2011-01-18"
    assert r["docno_text"].startswith("府授農地字第1130041756號")
    keys = [a["key"] for a in r["articles"]]
    assert keys == [f"P{i}" for i in range(1, 24)]
    p4 = r["articles"][3]["text"]
    assert "百分之四十" in p4 and "\n（一）依畜牧法申請畜牧設施。" in p4
    assert all(a["url"].startswith("https://law.taichung.gov.tw/Download.ashx") for a in r["attachments"])
    h = parse_glrs_history((fixtures / "local/taichung_lawsource_GL000357.html").read_text(encoding="utf-8"))
    assert [x["date"] for x in h] == ["2011-01-18", "2014-05-27", "2020-08-10", "2024-02-21"]


def test_parse_articles_rejoins_wrapped_lines(fixtures):
    r = parse_glrs_law((fixtures / "local/taichung_lawcontent_GL002048.html").read_text(encoding="utf-8"), URL + "GL002048")
    a1 = r["articles"][0]
    assert a1["key"] == "1" and a1["label"] == "第 1 條" and a1["chapter"] == "第一章 總則"
    assert a1["text"] == "本辦法依都市計畫法臺中市施行自治條例（以下簡稱本自治條例）第三十五條第四項及第三十八條第四項規定訂定之。"
    a4 = next(a for a in r["articles"] if a["key"] == "4")
    assert a4["text"].count("\n") == 2  # 三項
    assert "　" not in "".join(a["text"] for a in r["articles"])


def test_sync_local_and_manifest(data_dir):
    log = Run("daily", client=FakeClient(), only=["local-taichung"]).execute()
    s = log["sources"][0]
    assert s["status"] == "ok" and s["added"] == 4
    law = Store(paths.LAWS).get("TXG-GL000357")
    assert law["county"] == "臺中市" and law["primary_source"] == "local-taichung"
    assert law["official_url"] == URL + "GL000357"
    assert law["review"]["reviewed_at"] and "material" in law["scenarios"]
    assert (paths.LAWS / "versions" / "TXG-GL000357").exists()
    cands = read_json(paths.META / "local-candidates.json")
    assert "臺中市" in cands
    assert all(c["law_system_id"] not in ("GL000357", "GL002048") for c in cands["臺中市"]["candidates"])
    from agrilaw.indexing import build
    build()
    m = read_json(paths.WEB_DATA / "manifest.json")
    tc = next(c for c in m["counties"] if c["name"] == "臺中市")
    assert tc["checked"] and tc["laws"] == 4
    assert next(c for c in m["counties"] if c["name"] == "臺北市")["checked"] is False
    idx = {l["id"]: l for l in read_json(paths.WEB_DATA / "search-laws.json")}
    assert idx["TXG-GL000357"]["cty"] == "臺中市" and idx["TXG-GL000357"]["u"] == URL + "GL000357"
    # second run: unchanged
    log2 = Run("daily", client=FakeClient(), only=["local-taichung"]).execute()
    assert log2["sources"][0]["unchanged"] == 4 and log2["sources"][0]["modified"] == 0


def test_outage_keeps_existing_local_law(data_dir):
    Run("daily", client=FakeClient(), only=["local-taichung"]).execute()
    before = Store(paths.LAWS).get("TXG-GL000357")
    log = Run("daily", client=FakeClient(down=["law.taichung"]), only=["local-taichung"]).execute()
    assert log["sources"][0]["status"] == "failed"
    assert Store(paths.LAWS).get("TXG-GL000357")["content_hash"] == before["content_hash"]


def test_county_without_auto_sync_is_not_fetched(data_dir, monkeypatch):
    import agrilaw.sync as sync_mod
    cfg = [dict(c) for c in counties()]
    cfg[0]["auto_sync"] = False
    monkeypatch.setattr(sync_mod, "counties", lambda: cfg)
    c = FakeClient()
    log = Run("daily", client=c, only=["local-taichung"]).execute()
    assert log["sources"][0]["status"] == "unavailable" and not c.calls


def test_every_county_listed_once():
    names = [c["name"] for c in counties()]
    assert len(names) == 22 == len(set(names))
    for c in counties():
        if c.get("auto_sync"):
            assert c["checked"] and c["law_system"].startswith("https://") and c["source_id"].startswith("local-")
            for law in c["laws"]:
                assert law["law_system_id"] and law["reviewed_at"], law
