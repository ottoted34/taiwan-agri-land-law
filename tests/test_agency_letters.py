"""林保署公文函釋、農業綠能函釋：解析、與既有（RMIS）函釋合併、失敗不影響既有資料。"""
from agrilaw import paths
from agrilaw.collectors.agency_letters import forest_relevant, parse_forest_detail, parse_forest_list, parse_talis_detail, parse_talis_list
from agrilaw.store import Store
from agrilaw.sync import Run
from fakeclient import FakeClient


def read(fixtures, name):
    return (fixtures / "agency" / name).read_text(encoding="utf-8")


def test_parsers(fixtures):
    rows, last = parse_forest_list(read(fixtures, "forest_list_p1.html"))
    assert len(rows) == 10 and last == 103 and rows[0]["docno_text"] == "農林業字第1152440541號"
    d = parse_forest_detail(read(fixtures, "forest_detail_0001089.html"))
    assert d["date_text"] == "115/10/01" and d["content"].startswith("一、查本部106年12月12日") and "正本:" in d["content"]
    rows, last = parse_talis_list(read(fixtures, "talis_list_p1.html"))
    assert len(rows) == 8 and last == 14 and rows[0]["posted"] == "2026-08-21"
    d = parse_talis_detail(read(fixtures, "talis_detail_0056447d.html"))
    assert d["docno_text"] == "農農保字第1142655512號" and d["date_text"] == "中華民國114年1月23日"
    assert d["subject"].startswith("綠能設施之附屬設施") and "第27條規定" in d["content"] and "返回" not in d["content"]


def test_talis_merges_into_existing_rmis_letter(data_dir):
    Store(paths.INTERP).put({"id": "itp-x", "docno": "農農保字第1142655512號", "date": "2025-01-23", "subject": "綠能設施附屬設施",
                             "content": "RMIS 原文", "sources": [{"source_id": "rmis-interpretations", "url": "u", "source_key": "rmis:1"}],
                             "validity": {"status": "no_known_cessation", "basis": [], "confirmed": False}})
    log = Run("daily", client=FakeClient(), only=["talis-green-energy"]).execute()
    s = log["sources"][0]
    assert s["status"] == "ok" and s["added"] == 0 and s["unchanged"] == 16
    rec = Store(paths.INTERP).get("itp-x")
    assert rec["content"] == "RMIS 原文"  # 不覆寫既有內容
    assert {x["source_id"] for x in rec["sources"]} == {"rmis-interpretations", "talis-green-energy"}
    assert len(list(Store(paths.INTERP).all())) == 1


def test_forest_new_letter_and_outage(data_dir):
    log = Run("daily", client=FakeClient(), only=["forest-interpretations"]).execute()
    s = log["sources"][0]
    assert s["status"] == "ok" and s["added"] == 1
    rec = next(Store(paths.INTERP).all())
    assert rec["docno"] == "農林業字第1152440541號" and rec["date"] == "2026-10-01"
    assert rec["sources"][0]["url"] == "https://www.forest.gov.tw/0000062/0001089"
    assert rec["category"] == "森林產業組／山坡地開發利用回饋金繳交辦法"
    log = Run("daily", client=FakeClient(down=["forest.gov.tw"]), only=["forest-interpretations"]).execute()
    assert log["sources"][0]["status"] == "failed"
    assert Store(paths.INTERP).get(rec["id"])["content"] == rec["content"]


def test_forest_filter_is_narrow():
    assert forest_relevant({"law": "山坡地開發利用回饋金繳交辦法", "subject": "回饋金疑義"})
    assert forest_relevant({"law": "森林法", "subject": "林業用地作林業設施容許使用疑義"})
    assert not forest_relevant({"law": "森林法", "subject": "國有林產物處分疑義"})
    assert not forest_relevant({"law": "野生動物保育法", "subject": "保育類野生動物飼養疑義"})
