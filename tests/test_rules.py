from agrilaw.agencies import resolve
from agrilaw.relations import extract_refs
from agrilaw.validity import cessation_signals, history_articles


def test_history_articles():
    assert history_articles("修正發布第 6、23、27～30、32、33 條條文") == {"6", "23", "27", "28", "29", "30", "32", "33"}
    assert history_articles("修正發布全文 37 條；並自發布日施行") == "ALL"
    assert history_articles("增訂第 29-1 條條文") == {"29-1"}
    assert history_articles("公告第 9 條所列屬「行政院農業委員會」之權責事項，自一百十二年八月一日起改由「農業部」管轄") == set()


def test_extract_refs():
    names = {"申請農業用地作農業設施容許使用審查辦法": "M0020022", "農業發展條例": "M0020001"}
    refs = extract_refs("依「申請農業用地作農業設施容許使用審查辦法」第26條規定…復依農業發展條例第八條之一", names)
    got = {(r["law_id"], r["article"]) for r in refs}
    assert got == {("M0020022", "26"), ("M0020001", "8-1")}


def test_cessation_signal_requires_explicit_wording():
    rec = {"docno": "農保規字第1150000001號", "subject": "停止適用",
           "content": "本部前於110年1月1日農企字第1100000001號函，自即日起停止適用。另依農企字第1090000001號函說明辦理。",
           "category": "解釋函"}
    sig = cessation_signals(rec)
    assert {s["target"] for s in sig if s["kind"] == "cease"} == {"農企字第1100000001號"}


def test_historical_agency():
    r = resolve("行政院農業委員會", "2015-01-01")
    assert r["is_historical"] and r["agency_id"] == "moa"
    r = resolve("行政院農業委員會水土保持局", "2015-01-01")
    assert r["historical_name"] == "行政院農業委員會水土保持局" and r["agency_id"] == "ardswc"
    r = resolve("農業部農村發展及水土保持署", "2026-01-01")
    assert not r["is_historical"] and r["agency_id"] == "ardswc"


def test_afa_doc_prefix_inferred_when_issuer_missing():
    from agrilaw.agencies import resolve
    r = resolve("", "2025-07-23", "農糧資字第1141149457號")
    assert r["agency_id"] == "afa" and not r["is_historical"] and r["agency_inferred"]
    r = resolve("", "2015-01-01", "農糧企字第1040000001號")
    assert r["agency_id"] == "afa" and r["is_historical"] and "農糧署" in r["historical_name"]
    assert resolve("", "2016-11-14", "農授糧字第1051061342號")["agency_id"] != "afa"  # 授權函仍屬農委會／農業部名義
