import json

from agrilaw.articles import article_key, split_fulltext_articles
from agrilaw.collectors.moj_law import normalize_law
from agrilaw.collectors.rmis import (parse_directory, parse_law_detail, parse_law_exp, parse_law_history,
                                     parse_news_detail, parse_news_list)
from agrilaw.util import find_docnos, normalize_docno, roc_to_iso


def r(f, p):
    return (f / p).read_text(encoding="utf-8")


def test_roc_dates():
    assert roc_to_iso("115/7/28") == "2026-07-28"
    assert roc_to_iso("民國115年7月28日") == "2026-07-28"
    assert roc_to_iso("089年03月27日") == "2000-03-27"
    assert roc_to_iso("20251231") == "2025-12-31"
    assert roc_to_iso("1150728") == "2026-07-28"
    assert roc_to_iso("115/2/30") is None


def test_docno_normalisation():
    assert normalize_docno("農保規字第 1150230515 號") == "農保規字第1150230515號"
    assert normalize_docno("農企字第１０１０７３１３８３號") == "農企字第1010731383號"
    assert normalize_docno("農企字第1100012423a號") == "農企字第1100012423A號"
    assert find_docnos("依前開102年10月7日農授糧字第1020723962號函及農農保字第1142655512號函") == [
        "農授糧字第1020723962號", "農農保字第1142655512號"]


def test_docno_with_date_prefix():
    from agrilaw.util import date_in_text
    assert normalize_docno("二月五日農授糧字第0931001784號") == "農授糧字第0931001784號"
    assert normalize_docno("七日台八九內中地字第8906564號") == "台八九內中地字第8906564號"
    assert date_in_text("九十三年四月六日農糧企字○九三一○七○三六七號函") == "2004-04-06"
    assert date_in_text("二月五日農授糧字第0931001784號") is None


def test_article_keys():
    assert article_key("第 8-1 條") == "8-1"
    assert article_key("第八條之一") == "8-1"
    assert article_key("第一百零五條") == "105"
    assert article_key("第29-1條") == "29-1"


def test_rmis_news_list(fixtures):
    rows, last = parse_news_list(r(fixtures, "live/rmis_newslist_p1.html"))
    assert last == 172 and len(rows) == 10
    assert rows[0] == {"rmis_id": 6075, "date_text": "115/7/28", "docno_text": "農保規字第1150230515號",
                       "subject": "有關貴局所詢申請農業用地作綠能設施之「綠能附屬設施(變電箱)」審認原則疑義案，復如說明，請查照。",
                       "category": "解釋函"}


def test_rmis_news_detail_verbatim(fixtures):
    d = parse_news_detail(r(fixtures, "live/rmis_newsdetail_6075.html"))
    assert d["agency_text"] == "農業部農村發展及水土保持署"
    assert d["docno_text"] == "農保規字第1150230515號"
    assert "，" in d["subject"] and "," not in d["subject"]  # official punctuation preserved
    assert d["content"].startswith("一、按農業設施倘為經營需要")
    assert "\n二、" in d["content"]


def test_rmis_invalid_detail_is_none(fixtures):
    assert parse_news_detail(r(fixtures, "live/rmis_newsdetail_100.html")) is None


def test_rmis_directory_and_law(fixtures):
    d = parse_directory(r(fixtures, "live/rmis_directory.html"))
    assert sum(not x["external"] for x in d) == 24
    law = parse_law_detail(r(fixtures, "live/rmis_lawdetail_2013.html"))
    assert law["name"] == "申請農業用地作農業設施容許使用審查辦法"
    keys = [a["key"] for a in law["articles"]]
    assert keys[:3] == ["1", "2", "3"] and "29-1" in keys and len(keys) == 38
    assert len(law["histories"]) == 17 and law["histories"][0]["date"] == "2025-12-31"
    assert len(law["attachments"]) == 5 and law["attachments"][0]["url"].endswith(".pdf")
    rule = parse_law_detail(r(fixtures, "live/rmis_lawdetail_3008.html"))
    pk = [a["key"] for a in rule["articles"]]
    assert "P7-1" in pk and len(pk) == len(set(pk))


def test_rmis_history_versions(fixtures):
    full = parse_law_history(r(fixtures, "live2/rmis_lawhistory_68.html"))
    assert full["is_full_text"] and full["date"] == "2003-12-15" and len(full["articles"]) == 28
    part = parse_law_history(r(fixtures, "live2/rmis_lawhistory_211.html"))
    assert not part["is_full_text"] and part["articles"] == []


def test_rmis_law_exp(fixtures):
    e = parse_law_exp(r(fixtures, "live2/rmis_lawexp_2013.html"))
    assert len(e["items"]) == 354
    assert e["items"][0]["docno"] == "農企字第1010731383號"


def test_moj_normalise(fixtures):
    data = json.loads(r(fixtures, "live/moj_order_subset.json"))
    law = next(normalize_law(x, "命令") for x in data["Laws"] if x["LawName"].startswith("申請農業用地"))
    assert law["id"] == "M0020022" and law["modified_date"] == "2025-12-31"
    assert law["articles"][0]["chapter"].strip().startswith("第 一 章")
    assert [h["date"] for h in law["histories"]][:2] == ["2003-12-15", "2009-03-16"]
    assert len(law["histories"]) == 17
    assert law["attachments"][0]["url"].startswith("https://law.moj.gov.tw/")


def test_split_fulltext():
    arts = split_fulltext_articles("第 一 章 總則\n\n第一條\n本辦法依據。\n\n第二條\n適用範圍如下：\n一、耕地。")
    assert [a["key"] for a in arts] == ["1", "2"] and arts[1]["text"].endswith("一、耕地。")


def test_datamoa_dates_and_personal_data_guard():
    from agrilaw.collectors.datamoa import PERSONAL_FIELDS, _ym
    assert _ym("11508") == "2026-08"
    assert _ym("202606") == "2026-06"
    assert _ym("105年6月") == "2016-06"
    assert _ym("2017-11-01") == "2017-11-01"
    assert {"姓名", "電子信箱"} <= PERSONAL_FIELDS
