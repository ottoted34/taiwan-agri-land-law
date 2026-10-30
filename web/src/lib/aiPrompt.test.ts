import { describe, expect, it } from "vitest";
import { buildAiPrompt, maskPII, type PromptInput } from "./aiPrompt";

const base: PromptInput = {
  scenario: "農業資材室", county: "臺中市", countyNote: "本站已收錄 2 部地方規定", facts: "申請人於一般農業區種植芒果約0.5公頃", caseDate: "2024-05-01",
  openQuestions: ["土地使用分區"], dataVersion: "2026-10-30",
  laws: [{ name: "臺中市申請農業用地作農業設施容許使用審查要點", level: "行政規則", county: "臺中市", modified: "2024-02-21",
    officialUrl: "https://law.taichung.gov.tw/LawContent.aspx?id=GL000357", siteUrl: "https://x/#/law/TXG-GL000357",
    articles: [{ label: "第 4 點", text: "農業設施總面積，不得超過百分之四十。" }], amendmentsAfterCase: [] }],
  interps: [{ docno: "農保規字第1150230515號", date: "2026-07-28", agency: "農業部農村發展及水土保持署", subject: "資材室疑義", content: "依附表一…",
    officialUrl: "https://rmis.ardswc.gov.tw/Web/NewsDetail.aspx?id=1", siteUrl: "https://x/#/interp/a", validity: "未查得停止適用",
    validityConfirmed: false, validityNotes: [], lastSynced: "2026-10-30T10:00:00+08:00" }],
  tech: [],
};

describe("AI prompt", () => {
  it("contains the required rules, format and cited material", () => {
    const p = buildAiPrompt(base);
    for (const s of ["只能引用", "不得自行創造", "依所附資料無法判斷", "不得作出准許、駁回", "一、法規依據", "二、函釋見解", "三、本案事實", "四、適用分析", "五、待查事項", "六、建議處理方向"])
      expect(p).toContain(s);
    expect(p).toContain("[法1] 臺中市申請農業用地作農業設施容許使用審查要點（臺中市・行政規則");
    expect(p).toContain("[函1] 發文字號：農保規字第1150230515號｜發文日期：民國115/07/28");
    expect(p).toContain("官方連結：https://rmis.ardswc.gov.tw/Web/NewsDetail.aspx?id=1");
    expect(p).toContain("效力查核：未查得停止適用（系統比對，非效力認定）");
    expect(p).toContain("（本次未檢索到技術參考資料）");
  });
  it("marks missing dates instead of inventing them", () => {
    const p = buildAiPrompt({ ...base, interps: [{ ...base.interps[0], date: null, officialUrl: null }] });
    expect(p).toContain("發文日期：官方頁面未載");
    expect(p).toContain("官方連結：附件未載");
  });
  it("truncates long letters", () => {
    const p = buildAiPrompt({ ...base, interps: [{ ...base.interps[0], content: "甲".repeat(5000) }] });
    expect(p).toContain("以下省略，全文見連結");
    expect(p.length).toBeLessThan(8000);
  });
});

describe("maskPII", () => {
  it("masks ID numbers, phones, land numbers and addresses", () => {
    const r = maskPII("A123456789 君，電話0912-345-678，坐落○○段123-4地號，住中山路一段12巷3號");
    expect(r.text).not.toMatch(/A123456789|0912|123-4地號|3號/);
    expect(r.count).toBe(4);
  });
  it("leaves official document numbers and areas alone", () => {
    const s = "依府授農地字第1130041756號令，面積0.5公頃，第4點";
    expect(maskPII(s)).toEqual({ text: s, count: 0 });
  });
});
