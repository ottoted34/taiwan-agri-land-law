/**
 * 「複製給 AI」：把案件審查輔助檢索到的資料整理成可貼到 ChatGPT、Claude 等生成式 AI 的提示詞。
 * 本站不呼叫任何 AI 服務、不需帳號或 API Key；提示詞只在使用者瀏覽器產生，由使用者自行貼上。
 * 提示詞內以 [法1]、[函1]、[技1] 編號附件，要求 AI 只能引用附件、不得自創字號、不作准駁結論。
 */
import { roc } from "./text";

export const SITE = "https://ottoted34.github.io/taiwan-agri-land-law/#";

export interface PromptLaw {
  name: string; level: string; county?: string | null; modified: string | null; officialUrl: string | null; siteUrl: string;
  articles: { label: string; text: string }[]; amendmentsAfterCase: string[];
}
export interface PromptInterp {
  docno: string; date: string | null; agency: string; subject: string; content: string; officialUrl: string | null; siteUrl: string;
  validity: string; validityConfirmed: boolean; validityNotes: string[]; lastSynced: string | null;
}
export interface PromptTech { title: string; agency: string; date: string | null; url: string | null; siteUrl: string }
export interface PromptInput {
  scenario: string; county: string | null; countyNote: string; facts: string; caseDate: string | null; openQuestions: string[];
  dataVersion: string; laws: PromptLaw[]; interps: PromptInterp[]; tech: PromptTech[];
}

export const INTERP_MAX = 900;
export const ARTICLE_MAX = 700;

/** 遮蔽常見個資樣式（身分證／居留證號、手機、市話、地號、門牌）。只是補救措施，使用者仍不應輸入個資。 */
export function maskPII(s: string): { text: string; count: number } {
  let count = 0;
  const rep = (re: RegExp, to: string) => { s = s.replace(re, (...m) => { count++; return to.replace("$1", m[1] ?? ""); }); };
  rep(/(?<![A-Za-z0-9])[A-Z][1289]\d{8}(?!\d)/gi, "〔身分證號已遮蔽〕");
  rep(/(?<!\d)09\d{2}[-\s]?\d{3}[-\s]?\d{3}(?!\d)/g, "〔電話已遮蔽〕");
  rep(/(?<!\d)\(?0\d{1,2}\)?[-\s]\d{3,4}[-\s]?\d{4}(?!\d)/g, "〔電話已遮蔽〕");
  rep(/[\d０-９]+(?:[-－之][\d０-９]+)?\s*地號/g, "○○地號");
  rep(/([路街段巷弄])[\d０-９巷弄之\-－]*[\d０-９]+\s*號/g, "$1○○號");
  return { text: s, count };
}

const clip = (s: string, n: number) => {
  const t = s.replace(/\s+/g, " ").trim();
  return t.length > n ? t.slice(0, n) + `……（以下省略，全文見連結）` : t;
};

export function buildAiPrompt(p: PromptInput): string {
  const facts = maskPII(p.facts.trim()).text;
  const L: string[] = [];
  L.push(
    "# 角色與任務",
    "你是協助農地管理承辦人整理審查意見的助理。請依下方「附件資料」分析本案，產出供承辦人參考的分析草稿。",
    "",
    "# 必須遵守的規則",
    "1. 只能引用本提示詞「附件資料」所列之法規條文、函釋與技術參考資料，並以附件編號（如 [法1]、[函2]、[技1]）標註出處；不得引用附件以外之法規、函釋、判決或網路資料。",
    "2. 不得自行創造、推測、補全或改寫任何發文字號、日期、條號或機關名稱；引用時須與附件所載完全一致。附件未載者，一律寫「附件未載」。",
    "3. 附件資料不足以判斷時，必須明白寫出「依所附資料無法判斷」並列入「待查事項」，不得臆測或以一般常識補足。",
    "4. 不得作出准許、駁回、合法或違法之結論；只能提供分析與建議處理方向，最終由權責機關依法及個案事實審認。",
    "5. 每件函釋附有「效力查核」資訊：「未查得停止適用」不等於確認仍有效；標示停止適用、廢止、可能受修法影響或待查核者，應提醒承辦人不宜逕予援用並列入待查事項。",
    "6. 函釋係針對當時個案事實或法規版本作成，引用時應比對其前提事實與本案是否相同，並說明異同。",
    "7. 技術參考資料不具法律效力，只能用於說明農業經營合理性或設施需求。",
    "8. 地方自治法規只適用於所標示之縣市；若附件未含本案縣市之地方規定，應提醒承辦人另查。",
    "9. 案件日期之後法規曾修正者，應提醒確認案件適用之法規版本。",
    "",
    "# 輸出格式（請依序使用以下標題）",
    "一、法規依據：列出可能適用之條文（附件編號＋法規名稱＋條次），說明各條要件。",
    "二、函釋見解：列出相關函釋（附件編號＋字號＋日期），摘要見解、前提事實與效力查核狀態。",
    "三、本案事實：僅整理「案件資料」中已知事實，不得自行補充。",
    "四、適用分析：逐項比對法規要件、函釋見解與本案事實，指出符合、不符合或無法判斷之處。",
    "五、待查事項：列出需補正、現場勘查或向上級機關查證之事項。",
    "六、建議處理方向：提出程序上之處理建議（如補正、會勘、函請釋示），不作准駁結論。",
    "",
    "# 案件資料",
    `- 審查情境：${p.scenario}`,
    `- 縣市：${p.county || "未指定"}${p.countyNote ? `（${p.countyNote}）` : ""}`,
    `- 案件日期：${p.caseDate ? roc(p.caseDate, true) : "未提供"}`,
    "- 已知事實（承辦人輸入，已去識別化）：",
    facts ? facts.split("\n").map((x) => "  " + x).join("\n") : "  （未提供；請以待查事項處理）",
    "- 系統列出之待釐清事項：",
    ...p.openQuestions.map((q) => `  ・${q}`),
    "",
    `# 附件資料（資料來源：農地法規函釋知識庫，非官方整理；資料版本 ${p.dataVersion}；以官方連結內容為準）`,
    "",
    "## 法規條文",
  );
  if (!p.laws.length) L.push("（本次未檢索到法規條文）");
  p.laws.forEach((l, i) => {
    L.push(`[法${i + 1}] ${l.name}（${l.county ? l.county + "・" : ""}${l.level || "法規"}；最新修正 ${l.modified ? roc(l.modified, true) : "日期不詳"}）`,
      `  官方連結：${l.officialUrl || "附件未載"}`, `  本站頁面：${l.siteUrl}`);
    if (l.amendmentsAfterCase.length) L.push(`  注意：案件日期後曾修正 ${l.amendmentsAfterCase.length} 次（${l.amendmentsAfterCase.slice(0, 4).join("；")}），請確認適用版本。`);
    if (!l.articles.length) L.push("  （未檢索到相關條文，請至官方連結查閱）");
    for (const a of l.articles) L.push(`  ・${a.label}：${clip(a.text, ARTICLE_MAX)}`);
  });
  L.push("", "## 函釋");
  if (!p.interps.length) L.push("（本次未檢索到函釋）");
  p.interps.forEach((x, i) => {
    L.push(`[函${i + 1}] 發文字號：${x.docno || "附件未載"}｜發文日期：${x.date ? roc(x.date, true) : "官方頁面未載"}｜機關：${x.agency || "附件未載"}`,
      `  主旨：${x.subject}`,
      `  內容：${clip(x.content || "", INTERP_MAX) || "附件未載"}`,
      `  官方連結：${x.officialUrl || "附件未載"}`, `  本站頁面：${x.siteUrl}`,
      `  效力查核：${x.validity}（${x.validityConfirmed ? "人工確認" : "系統比對，非效力認定"}）${x.validityNotes.length ? "；" + x.validityNotes.join("；") : ""}${x.lastSynced ? `；本站最後確認 ${x.lastSynced.slice(0, 10)}` : ""}`);
  });
  L.push("", "## 技術參考資料（不具法律效力）");
  if (!p.tech.length) L.push("（本次未檢索到技術參考資料）");
  p.tech.forEach((t, i) => L.push(`[技${i + 1}] ${t.title}（${t.agency}，${t.date ? roc(t.date) : "年月不詳"}）${t.url ? "　" + t.url : ""}　本站：${t.siteUrl}`));
  L.push("", "請依上述規則與輸出格式作答。如附件資料彼此矛盾，請指出矛盾之處，不要自行取捨。");
  return L.join("\n");
}
