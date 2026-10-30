"""課程摘錄之函釋：匯入、標示非原文、官方原文收錄後自動移除。"""
from agrilaw import paths
from agrilaw.store import Store
from agrilaw.sync import Run
from agrilaw.util import load_yaml


def course_records():
    return [r for r in Store(paths.INTERP).all() if r["sources"][0]["source_id"] == "course-summaries"]


def test_import_and_replace_by_official(data_dir):
    items = load_yaml(paths.CONFIG / "relations" / "course_summaries.yaml")["items"]
    log = Run("daily", client=None, only=["course-summaries"]).execute()
    assert log["sources"][0]["added"] == len(items) == 50
    recs = course_records()
    one = next(r for r in recs if r["docno"] == "農糧企字第1031012987號")
    assert one["category"] == "課程摘錄" and "course_summary" in one["flags"]
    assert one["sources"][0]["url"] is None and "非函釋原文" in one["memo"]
    assert one["subject"].startswith("（課程摘錄）所詢得否於農業資材室放置耕耘機")
    assert one["agency_id"] == "afa"
    assert next(r for r in recs if r["docno"] == "內營字第8904763號")["agency_text"] == "內政部"
    # 官方來源收錄同字號＋日期後，下次匯入即移除摘錄
    Store(paths.INTERP).put({"id": "itp-official", "docno": one["docno"], "date": one["date"], "subject": "官方原文",
                             "content": "原文", "sources": [{"source_id": "rmis-interpretations", "url": "u", "source_key": "rmis:9"}],
                             "validity": {"status": "no_known_cessation", "basis": [], "confirmed": False}})
    log = Run("daily", client=None, only=["course-summaries"]).execute()
    assert log["sources"][0]["status_changed"] == 1
    assert Store(paths.INTERP).get(one["id"]) is None and len(course_records()) == 49
