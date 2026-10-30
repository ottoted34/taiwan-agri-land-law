import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getInterp, getInterps, getLaws, getManifest, getTech } from "../lib/data";
import { buildAiPrompt, maskPII, SITE } from "../lib/aiPrompt";
import { CountySelect, countyInfo, LocalTag } from "../components/county";
import { SCENARIOS, type Scenario } from "../lib/scenarios";
import { articleAnchor, articleName, norm, roc, rocToIso } from "../lib/text";
import type { InterpDetail, InterpIdx, LawIdx, Manifest, TechIdx } from "../lib/types";
import { CopyButton, ErrorBox, Loading, TypeTag, useAsync, ValidityTag, VALIDITY_SHORT } from "../components/ui";

export default function Assist() {
  const d = useAsync(() => Promise.all([getManifest(), getLaws(), getInterps(), getTech()]), []);
  const [sid, setSid] = useState("material");
  const [facts, setFacts] = useState("");
  const [caseDate, setCaseDate] = useState("");
  const [county, setCounty] = useState(() => { try { return localStorage.getItem("assist-county") || ""; } catch { return ""; } });
  const pickCounty = (c: string) => { setCounty(c); try { localStorage.setItem("assist-county", c); } catch { /* storage unavailable */ } };
  if (d.error) return <ErrorBox msg={d.error} />;
  if (!d.data) return <Loading />;
  const [man, laws, interps, tech] = d.data;
  const sc = SCENARIOS.find((s) => s.id === sid)!;
  return <>
    <h1>案件審查輔助</h1>
    <div className="callout danger" style={{ marginBottom: 14 }}><strong>重要說明</strong>：本工具以「檢索＋規則」整理可能相關之法規、函釋與技術資料及檢核事項，<strong>不是 AI 法律分析，不提供准駁結論</strong>，
      不能取代權責機關之審查。所有產出均為<strong>草稿</strong>，需由承辦人依現行法規、官方附表及個案事實查證後使用；請勿輸入民眾姓名、身分證字號、地號等個人資料（本頁資料僅在您的瀏覽器處理，不會傳送或儲存）。</div>
    <div className="layout-search">
      <aside className="card filters">
        <strong>1. 選擇情境</strong>
        <div style={{ display: "grid", gap: 4, marginTop: 6 }}>{SCENARIOS.map((s) =>
          <button key={s.id} className={`chip ${s.id === sid ? "on" : ""}`} style={{ textAlign: "left", borderRadius: 6 }} onClick={() => setSid(s.id)}>{s.title}</button>)}</div>
      </aside>
      <section>
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="row" style={{ marginBottom: 8 }}><strong>2. 案件所在縣市</strong><CountySelect man={man} value={county} onChange={pickCounty} /></div>
          <strong>3. 輸入案件客觀事實（選填）</strong>
          <textarea className="case" value={facts} onChange={(e) => setFacts(e.target.value)} placeholder="例：申請人於一般農業區農牧用地種植芒果約0.5公頃，申請設置農業資材室，擬存放肥料、套袋及噴藥器具……（請勿輸入個人資料）" />
          <label className="small">申請或案件事實發生日期（民國或西元，用於檢查法規修正前後）：
            <input value={caseDate} onChange={(e) => setCaseDate(e.target.value)} placeholder="例 113/5/1" style={{ marginLeft: 6, border: "1px solid var(--line-strong)", borderRadius: 6, padding: "3px 8px" }} /></label>
          {caseDate && !rocToIso(caseDate) && <span className="small" style={{ color: "var(--danger)" }}> 日期格式無法辨識</span>}
        </div>
        <Report sc={sc} facts={facts} caseDate={rocToIso(caseDate)} county={county} man={man} laws={laws} interps={interps} tech={tech} />
      </section>
    </div>
  </>;
}

function Report({ sc, facts, caseDate, county, man, laws, interps, tech }: { sc: Scenario; facts: string; caseDate: string | null; county: string; man: Manifest; laws: LawIdx[]; interps: InterpIdx[]; tech: TechIdx[] }) {
  const r = useMemo(() => build(sc, facts, man, laws, interps, tech, caseDate, county), [sc, facts, man, laws, interps, tech, caseDate, county]);
  const text = toText(sc, facts, r, caseDate, county);
  const ci = countyInfo(man, county);
  return <div className="draft-box">
    <div className="row"><span className="tag draft">草稿・非正式公文</span><h2 style={{ margin: 0 }}>{sc.title}</h2><div className="spacer" /><CopyButton text={text} label="複製全文（純文字）" /></div>
    <p className="small muted">{sc.summary} 資料版本：{man.built_at.slice(0, 10)}。</p>

    <h3>A. 已知案件事實</h3>
    {facts.trim() ? <p className="doc" style={{ fontFamily: "inherit" }}>{facts}</p> : <p className="muted small">（尚未輸入）</p>}
    {r.factKeywords.length > 0 && <p className="small muted">事實中辨識到之關鍵詞：{r.factKeywords.join("、")}</p>}

    <h3>B. 待釐清事項</h3>
    <ul>{sc.facts.map((f) => <li key={f}>{f}</li>)}</ul>

    <h3>C. 可能適用的法規條文 <TypeTag kind="law" /></h3>
    {r.articles.length === 0 && <p className="muted small">本站尚未收錄情境所列法規，請至 <Link to="/laws">法規</Link> 查詢。</p>}
    {!county && <p className="small muted">未選擇縣市：僅列出全國性法規。地方自治法規、審查要點請於上方選擇縣市。</p>}
    {county && ci.checked && r.localCount === 0 && <p className="small muted">本站收錄之{county}地方規定中，未檢索到與本情境相關者（已收錄 {ci.laws} 部，見 <Link to={`/laws?county=${encodeURIComponent(county)}`}>{county}法規</Link>）。</p>}
    {county && !ci.checked && <div className="callout small" style={{ margin: "4px 0 8px" }}><strong>{county}：尚未查核</strong>。本站尚未收錄{county}之地方規定，請自行至該縣市法規查詢系統查詢；歡迎 <Link to="/sources#local">提供地方規定</Link>。</div>}
    {r.articles.map(({ law, items, amendments }) => <div key={law.id} style={{ marginBottom: 10 }}>
      <strong><Link to={`/law/${law.id}`}>{law.n}</Link></strong> {law.cty && <LocalTag county={law.cty} />} <span className="small muted">（最新修正 {roc(law.md)}）</span>
      {amendments.length > 0 && <div className="callout small" style={{ margin: "4px 0" }}>案件日期 {roc(caseDate)} 之後，本法規曾修正 {amendments.length} 次：{amendments.slice(0, 4).map((a) => { const d = a.text.replace(/^中華民國.*?(號令|號公告|號)/, "").slice(0, 40); return d ? `${roc(a.date)}（${d}）` : roc(a.date); }).join("；")}。請確認案件適用之法規版本（施行日期以官方公告為準）。</div>}
      <ul className="small">{items.map(([k, label, , t]) => <li key={k}><Link to={`/law/${law.id}#${articleAnchor(k)}`}>{label || articleName(k)}</Link>：{t.replace(/\s+/g, "").slice(0, 90)}…</li>)}</ul>
    </div>)}
    <p className="tiny muted">條文係依情境關鍵字自收錄之官方條文中檢索，可能有遺漏或不相關條文，請逐條確認適用條件。設施分類與面積請查官方附表。</p>

    <h3>D. 相關正式函釋 <TypeTag kind="interp" /></h3>
    {r.interps.length === 0 && <p className="muted small">未檢索到。可至 <Link to="/search?type=interp">函釋搜尋</Link> 調整關鍵字。</p>}
    <ol className="small">{r.interps.map(({ x, why }) => <li key={x.id} style={{ marginBottom: 6 }}>
      <Link to={`/interp/${x.id}`}>{x.ag || "（機關未載）"} {roc(x.d, true)} {x.no}</Link> <ValidityTag status={x.v} />
      <div>{x.s}</div><div className="tiny muted">檢索理由：{why}。與本案之相似與差異：請比對函釋所述前提事實（設施種類、經營內容、程序階段）是否與本案相同。</div></li>)}</ol>
    {r.interpTotal > r.interps.length && <Link className="small" to={`/search?type=interp&topic=${sc.interpTopics[0] || ""}`}>查看全部 {r.interpTotal} 件 →</Link>}

    <h3>E. 農業技術參考 <TypeTag kind="tech" /></h3>
    <div className="callout tech small">以下為試驗研究機構出版品書目，僅供判斷農業經營合理性、設施需求之專業參考，<strong>不具法律效力</strong>。</div>
    {r.tech.length === 0 ? <p className="muted small">未檢索到相關技術資料。</p> :
      <ul className="small">{r.tech.map((t) => <li key={t.id}><Link to={`/tech/${t.id}`}>{t.t}</Link>（{man.agency_names[t.ag] || t.ag}，{t.d ? roc(t.d) : "年月不詳"}）</li>)}</ul>}

    <h3>F. 審查檢核表</h3>
    <ul className="small" style={{ listStyle: "none", paddingLeft: 0 }}>{[...sc.checklist, "所引函釋之效力查核（是否有後續函釋、法規是否修正）", "所引條文是否為案件適用日期之有效版本"].map((c) => <li key={c}>☐ {c}</li>)}</ul>

    <h3>G. 初步研判（草稿）</h3>
    <ul className="small">
      {sc.cautions.map((c) => <li key={c}>{c}</li>)}
      <li>上列 B 項事實未釐清前，無法確定是否符合法定要件，<strong>不宜作成准駁結論</strong>。</li>
      {r.interps.some((i) => i.x.v !== "no_known_cessation") && <li>部分檢索到之函釋標示「{Array.from(new Set(r.interps.filter((i) => i.x.v !== "no_known_cessation").map((i) => VALIDITY_SHORT[i.x.v]))).join("、")}」，引用前應確認是否仍可援用。</li>}
      <li>建議處理方向：完成現場勘查及書面資料比對後，依 C 項條文逐項檢核；如事實與 D 項函釋前提不同，應敘明差異；有疑義時得函請上級主管機關釋示。</li>
    </ul>

    <AiCopy sc={sc} facts={facts} caseDate={caseDate} county={county} man={man} r={r} />

    <h3>附：審查意見／補正事項草稿</h3>
    <pre className="doc" style={{ fontFamily: "inherit", background: "var(--surface-2)", padding: 10, borderRadius: 6 }}>{draftText(sc, r)}</pre>
    <CopyButton text={draftText(sc, r)} label="複製草稿" />
  </div>;
}

interface Built {
  factKeywords: string[];
  articles: { law: LawIdx; items: LawIdx["a"]; amendments: { date: string; text: string }[] }[];
  interps: { x: InterpIdx; why: string }[]; interpTotal: number; tech: TechIdx[]; localCount: number;
}

function build(sc: Scenario, facts: string, man: Manifest, laws: LawIdx[], interps: InterpIdx[], tech: TechIdx[], caseDate: string | null, county: string): Built {
  const nf = norm(facts);
  const factKeywords = Array.from(new Set([...Object.values(man.topics.legal_topics).flatMap((t) => t.keywords), ...Object.values(man.topics.technical_topics).flatMap((t) => t.keywords)]
    .filter((k) => k.length >= 2 && nf.includes(norm(k))))).slice(0, 20);
  const byName = new Map(laws.map((l) => [l.n, l]));
  const articles = sc.laws.map(({ law, keywords }) => {
    const l = byName.get(law);
    if (!l) return null;
    const scored = l.a.map((a) => ({ a, s: keywords.reduce((n, k) => n + (a[3].includes(k) ? 1 : 0), 0) })).filter((x) => x.s > 0).sort((x, y) => y.s - x.s).slice(0, 6);
    return { law: l, items: scored.map((x) => x.a), amendments: [] as { date: string; text: string }[] };
  }).filter(Boolean) as Built["articles"];
  // 地方規定：只取所選縣市；依情境主題或關鍵字檢索，縣市未選時一律不列
  const localKw = Array.from(new Set([...sc.laws.flatMap((l) => l.keywords), ...sc.interpKeywords])).filter((k) => k.length >= 2);
  const local = laws.filter((l) => county && l.cty === county).map((l) => {
    // 管理者在 counties.yaml 指定之情境優先；未指定者才以主題、名稱或條文關鍵字判斷
    const relevant = l.scn && l.scn.length ? l.scn.includes(sc.id) || sc.id === "local"
      : sc.id === "local" || l.tp.some((t) => sc.interpTopics.includes(t)) || sc.laws.some(({ law }) => l.n.includes(law.replace(/(審查)?辦法$/, "")));
    if (!relevant) return null;
    const scored = l.a.map((a) => ({ a, s: localKw.reduce((n, k) => n + (a[3].includes(k) ? 1 : 0), 0) })).filter((x) => x.s > 0).sort((x, y) => y.s - x.s).slice(0, 6);
    return { law: l, items: scored.map((x) => x.a), amendments: [] as { date: string; text: string }[] };
  }).filter(Boolean) as Built["articles"];
  articles.push(...local);
  const lawIds = new Set(articles.map((a) => a.law.id));
  const kws = [...sc.interpKeywords, ...factKeywords].map(norm);
  const scoredI = interps.map((x) => {
    let s = 0; const why: string[] = [];
    const tp = sc.interpTopics.filter((t) => x.tp.includes(t));
    if (tp.length) { s += 3 * tp.length; why.push("主題：" + tp.map((t) => man.topics.legal_topics[t]?.label).join("、")); }
    const subj = norm(x.s);
    const hits = kws.filter((k) => k && subj.includes(k));
    if (hits.length) { s += 2 * hits.length; why.push("主旨含「" + Array.from(new Set(hits)).join("、") + "」"); }
    if (x.rel.some(([l]) => lawIds.has(l))) s += 1;
    return { x, s, why: why.join("；") };
  }).filter((y) => y.s >= 3).sort((a, b) => b.s - a.s || (b.x.d || "").localeCompare(a.x.d || ""));
  const ttp = new Set(sc.techTopics);
  const techHits = tech.filter((t) => t.tp.some((p) => ttp.has(p)) || factKeywords.some((k) => t.t.includes(k)))
    .sort((a, b) => (b.d || "").localeCompare(a.d || "")).slice(0, 8);
  if (caseDate) for (const a of articles) a.amendments = (a.law.h || []).filter(([d, t]) => d > caseDate && !/權責事項|改由.{0,10}管轄/.test(t)).map(([date, text]) => ({ date, text }));
  return { factKeywords, articles, interps: scoredI.slice(0, 12), interpTotal: scoredI.length, tech: ttp.size || factKeywords.length ? techHits : [], localCount: local.length };
}

function draftText(sc: Scenario, r: Built): string {
  const lawLines = r.articles.map((a) => `${a.law.n}${a.items.slice(0, 3).map((i) => (i[1] || articleName(i[0])).replace(/\s/g, "")).join("、")}`).join("；");
  return `【草稿】${sc.title}審查意見
一、法令依據：${lawLines || "（待補）"}（條文適用請依案件日期之有效版本確認）。
二、經查本案：（請填寫書面審查及現場勘查之客觀事實）。
三、待申請人補正或說明事項：
${sc.facts.slice(0, 6).map((f, i) => `  (${i + 1}) ${f}。`).join("\n")}
四、參考函釋：${r.interps.slice(0, 3).map((i) => `${i.x.no}（${roc(i.x.d, true)}）`).join("、") || "（無）"}；援用前應確認前提事實是否相同及效力查核資訊。
五、審查意見：（承辦人依上述事實及法令自行研判填寫）
※本草稿由「農地法規函釋知識庫」案件審查輔助產生，非正式公文，不得逕行對外發文。`;
}

function toText(sc: Scenario, facts: string, r: Built, caseDate: string | null, county: string): string {
  return [`【草稿・非正式公文】案件審查輔助：${sc.title}`, county ? `縣市：${county}` : "", caseDate ? `案件日期：${roc(caseDate, true)}` : "",
    "A. 已知案件事實", facts || "（未輸入）", "B. 待釐清事項", ...sc.facts.map((f) => "・" + f),
    "C. 可能適用的法規條文", ...r.articles.flatMap((a) => [a.law.cty ? `${a.law.n}（${a.law.cty}地方規定）` : a.law.n, ...a.items.map((i) => `  ${(i[1] || articleName(i[0]))}：${i[3].replace(/\s+/g, "")}`)]),
    "D. 相關正式函釋", ...r.interps.map((i) => `・${i.x.ag} ${roc(i.x.d, true)} ${i.x.no}：${i.x.s}（${VALIDITY_SHORT[i.x.v]}）`),
    "E. 農業技術參考（不具法律效力）", ...r.tech.map((t) => `・${t.t}`),
    "F. 審查檢核表", ...sc.checklist.map((c) => "☐ " + c), "G. 初步研判", ...sc.cautions, "B 項事實未釐清前，不宜作成准駁結論。",
    "", "※本內容由非官方網站產生，僅供參考。"].filter((x) => x !== "").join("\n");
}

/** 「複製給 AI」：預先載入檢索到之函釋明細（官方連結、效力查核），按下即複製，不送出任何資料。 */
function AiCopy({ sc, facts, caseDate, county, man, r }: { sc: Scenario; facts: string; caseDate: string | null; county: string; man: Manifest; r: Built }) {
  const ids = r.interps.map((i) => i.x.id);
  const det = useAsync(() => Promise.all(ids.map((id) => getInterp(id).catch(() => null))), [ids.join(",")]);
  const masked = maskPII(facts);
  const ci = countyInfo(man, county);
  const prompt = useMemo(() => {
    const byId = new Map<string, InterpDetail>((det.data || []).filter(Boolean).map((x) => [x!.id, x!]));
    return buildAiPrompt({
      scenario: sc.title, county: county || null, countyNote: !county ? "未選擇縣市，附件未含地方規定" : ci.checked ? `本站已收錄 ${ci.laws} 部地方規定` : "本站尚未查核此縣市地方規定",
      facts, caseDate, openQuestions: sc.facts, dataVersion: man.built_at.slice(0, 10),
      laws: r.articles.map((a) => ({ name: a.law.n, level: a.law.lv, county: a.law.cty, modified: a.law.md, officialUrl: a.law.u || null,
        siteUrl: `${SITE}/law/${a.law.id}`, articles: a.items.map((i) => ({ label: i[1] || articleName(i[0]), text: i[3] })),
        amendmentsAfterCase: a.amendments.map((m) => roc(m.date, true)) })),
      interps: r.interps.map(({ x }) => {
        const d = byId.get(x.id);
        const notes: string[] = [];
        for (const b of (d?.validity.basis || []) as Record<string, string>[]) {
          if (b.type === "law_amendment") notes.push(`${b.law_name}${b.article ? "第" + b.article + "條" : ""}於${roc(b.amended_on, true)}修正`);
          else if (b.by_docno) notes.push(`${b.by_docno}（${roc(b.by_date, true)}）${b.phrase || ""}`);
          else if (b.basis) notes.push(String(b.basis));
        }
        if (d?.source_missing_since) notes.push("官方來源已查無此筆，請至官方確認");
        return { docno: x.no, date: x.d, agency: x.ag, subject: x.s, content: x.c, officialUrl: d?.sources[0]?.url || null,
          siteUrl: `${SITE}/interp/${x.id}`, validity: VALIDITY_SHORT[x.v] || x.v, validityConfirmed: !!d?.validity.confirmed,
          validityNotes: Array.from(new Set(notes)).slice(0, 4), lastSynced: d?.last_synced || null };
      }),
      tech: r.tech.map((t) => ({ title: t.t, agency: man.agency_names[t.ag] || t.ag, date: t.d, url: t.u, siteUrl: `${SITE}/tech/${t.id}` })),
    });
  }, [det.data, sc, facts, caseDate, county, ci, man, r]);
  return <section className="card ai-box no-print" style={{ margin: "16px 0" }} aria-labelledby="ai-h">
    <div className="row"><h3 id="ai-h" style={{ margin: 0 }}>複製給 AI 分析</h3><div className="spacer" />
      {det.data ? <CopyButton text={prompt} label="複製給 AI（提示詞）" /> : <span className="small muted">整理函釋明細中…</span>}</div>
    <p className="small" style={{ margin: "6px 0" }}>將上方檢索到之法規條文、函釋（含字號、日期、官方連結、效力查核資訊）及技術參考資料，整理成可貼到 ChatGPT、Claude 等生成式 AI 的提示詞。
      提示詞已要求 AI <strong>只能引用所附資料、不得自創字號、資料不足時明說、不作准駁結論</strong>，並依「法規依據 → 函釋見解 → 本案事實 → 適用分析 → 待查事項 → 建議處理方向」格式回答。</p>
    <div className="callout danger small" role="note"><strong>使用前請注意</strong>：請勿在事實欄或 AI 對話中輸入<strong>姓名、身分證字號、地號、門牌、電話</strong>等個人資料；
      將資料貼到外部 AI 服務即屬傳送至第三方，請遵守所屬機關之<strong>生成式 AI 使用規定</strong>（如行政院「公部門人工智慧應用參考手冊」及機關內部規範），機密或限閱案件不得使用。
      AI 回答可能有誤，須由承辦人逐一核對官方原文。本站不登入、不保存、不傳送任何資料，也不需要 API Key。</div>
    {masked.count > 0 && <p className="small" style={{ color: "var(--danger)" }}>已自動遮蔽事實欄中疑似個資 {masked.count} 處（身分證號、電話、地號或門牌），請再自行檢查。</p>}
    <details className="small" style={{ marginTop: 6 }}><summary>預覽提示詞（{prompt.length.toLocaleString()} 字）</summary>
      <pre className="doc" style={{ maxHeight: 360, overflow: "auto", background: "var(--surface-2)", padding: 10, borderRadius: 6, whiteSpace: "pre-wrap" }}>{prompt}</pre></details>
  </section>;
}
