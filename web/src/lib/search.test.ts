import { describe, expect, it } from "vitest";
import { highlight, parseQuery, prepInterps, prepLaws, searchArticles, searchInterps } from "./search";
import type { InterpIdx, LawIdx } from "./types";
import { articleKey, roc, rocToIso } from "./text";

const syn = [["資材室", "農業資材室", "資材倉庫"]];
const names = { M0020022: "申請農業用地作農業設施容許使用審查辦法", M0020001: "農業發展條例" };
const it1: InterpIdx = { id: "a", no: "農保規字第1150230515號", d: "2026-07-28", ag: "農業部農村發展及水土保持署", agid: "ardswc", h: false, cat: "解釋函",
  s: "有關申請農業資材室容許使用疑義案", c: "依審查辦法附表一規定…", tp: ["material_room"], v: "no_known_cessation", rel: [["M0020022", "3", "extracted"]], fl: [] };
const it2: InterpIdx = { ...it1, id: "b", no: "農企字第1010731383號", d: "2012-08-30", ag: "行政院農業委員會", agid: "moa", h: true, s: "菇類栽培場起造人變更", c: "依原核定之計畫內容使用", tp: [], rel: [["M0020022", null, "official"]] };
const law: LawIdx = { id: "M0020001", n: "農業發展條例", lv: "法律", st: "current", md: "2016-11-30", tp: [], core: true, src: "moj",
  a: [["8-1", "第 8-1 條", null, "農業用地上申請以竹木、稻草、塑膠布或其他材料搭建無固定基礎之臨時性與農業生產有關之設施…"], ["3", "第 3 條", null, "本條例用詞，定義如下：…十二、農業使用…"]] };

describe("query parsing", () => {
  it("recognises 發文字號", () => {
    const q = parseQuery("農保規字第 1150230515 號", syn, names);
    expect(q.docno).toBe("農保規字第1150230515號");
    const hits = searchInterps(prepInterps([it1, it2]), q);
    expect(hits.map((h) => h.r.id)).toEqual(["a"]);
  });
  it("recognises law + article", () => {
    const q = parseQuery("農業發展條例第八條之一", syn, names);
    expect(q.lawHint).toBe("M0020001");
    expect(q.article).toBe("8-1");
    const hits = searchArticles(prepLaws([law]), q);
    expect(hits.map((h) => h.a.key)).toEqual(["8-1"]);
  });
  it("expands synonyms: 資材室 finds 農業資材室", () => {
    const hits = searchInterps(prepInterps([it1, it2]), parseQuery("資材室", syn, names));
    expect(hits.map((h) => h.r.id)).toEqual(["a"]);
  });
  it("ROC and AD dates", () => {
    expect(rocToIso("115/7/28")).toBe("2026-07-28");
    expect(rocToIso("2026-07-28")).toBe("2026-07-28");
    expect(searchInterps(prepInterps([it1, it2]), parseQuery("115/7/28", syn, names)).length).toBe(1);
    expect(roc("2026-07-28")).toBe("115/07/28");
  });
  it("AND semantics across terms", () => {
    expect(searchInterps(prepInterps([it1, it2]), parseQuery("菇類 起造人", syn, names)).map((h) => h.r.id)).toEqual(["b"]);
    expect(searchInterps(prepInterps([it1, it2]), parseQuery("菇類 資材室", syn, names)).length).toBe(0);
  });
  it("filters historical agency letters", () => {
    expect(searchInterps(prepInterps([it1, it2]), parseQuery("", syn, names), { historical: "only" }).map((h) => h.r.id)).toEqual(["b"]);
  });
  it("article keys", () => {
    expect(articleKey("第 8-1 條")).toBe("8-1");
    expect(articleKey("第一百零五條")).toBe("105");
  });
  it("highlights", () => {
    const parts = highlight("申請農業資材室容許使用", parseQuery("資材室", syn, names).terms);
    expect(parts.some(([t, m]) => m && t.includes("資材室"))).toBe(true);
  });
});
