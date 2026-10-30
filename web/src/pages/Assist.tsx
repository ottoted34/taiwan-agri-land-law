import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getInterps, getLaws, getManifest, getTech } from "../lib/data";
import { CountySelect, countyInfo, LocalTag } from "../components/county";
import { COMMON_FACTS, SCENARIOS, type Scenario } from "../lib/scenarios";
import { articleAnchor, articleName, norm, roc, rocToIso } from "../lib/text";
import type { InterpIdx, LawIdx, Manifest, TechIdx } from "../lib/types";
import { CourseTag, ErrorBox, Loading, TypeTag, useAsync, ValidityTag, VALIDITY_SHORT } from "../components/ui";

/** 常見主題：點選後加入事實欄，協助描述；不限定只能選這些 */
const HINTS = ["農用證明", "部分面積", "鋪設水泥", "填土", "貨櫃", "農業資材室", "農機具室", "溫室", "網室", "果樹", "農舍", "變更使用", "未依原核定計畫使用", "綠能"];

export default function Assist() {
  const d = useAsync(() => Promise.all([getManifest(), getLaws(), getInterps(), getTech()]), []);
  const [facts, setFacts] = useState("");
  const [caseDate, setCaseDate] = useState("");
  const [county, setCounty] = useState(() => { try { return localStorage.getItem("assist-county") || ""; } catch { return ""; } });
  const pickCounty = (c: string) => { setCounty(c); try { localStorage.setItem("assist-county", c); } catch { /* storage unavailable */ } };
  if (d.error) return <ErrorBox msg={d.error} />;
  if (!d.data) return <Loading />;
  const [man, laws, interps, tech] = d.data;
  const add = (k: string) => setFacts((f) => (f.includes(k) ? f : (f.trim() ? f.trim() + "，" : "") + k));
  return <>
    <h1>案件審查輔助</h1>
    <div className="callout danger" style={{ marginBottom: 14 }}><strong>重要說明</strong>：本工具依您輸入的案件事實，以「檢索＋規則」列出可能適用的法規與協助判斷之資料，<strong>不是 AI 法律分析，不提供准駁結論</strong>，
      不能取代權責機關之審查，請依現行法規、官方附表及個案事實查證後使用。請勿輸入民眾姓名、身分證字號、地號等個人資料（本頁資料僅在您的瀏覽器處理，不會傳送或儲存）。</div>
    <div className="card" style={{ marginBottom: 14 }}>
      <strong>案件事實</strong>
      <textarea className="case" value={facts} onChange={(e) => setFacts(e.target.value)} placeholder="例：申請人於一般農業區農牧用地種植芒果約0.5公頃，申請設置農業資材室，擬存放肥料、套袋及噴藥器具；現場有部分水泥鋪面……（請勿輸入個人資料）" />
      <div className="small muted" style={{ margin: "4px 0 6px" }}>常見主題（點選加入事實欄，也可直接自行描述）：</div>
      <div className="chips">{HINTS.map((k) => <button key={k} className="chip" onClick={() => add(k)}>{k}</button>)}</div>
      <div className="row" style={{ marginTop: 10, gap: 16 }}>
        <span className="row"><strong className="small">案件所在縣市</strong><CountySelect man={man} value={county} onChange={pickCounty} /></span>
        <label className="small">申請或事實發生日期（檢查法規修正前後）：
          <input value={caseDate} onChange={(e) => setCaseDate(e.target.value)} placeholder="例 113/5/1" style={{ marginLeft: 6, border: "1px solid var(--line-strong)", borderRadius: 6, padding: "3px 8px", width: 110 }} /></label>
        {caseDate && !rocToIso(caseDate) && <span className="small" style={{ color: "var(--danger)" }}>日期格式無法辨識</span>}
      </div>
    </div>
    {facts.trim().length < 2
      ? <p className="muted">請先輸入案件事實，系統會依內容判斷相關主題，列出可能適用的法規條文與協助判斷之資料。</p>
      : <Report facts={facts} caseDate={rocToIso(caseDate)} county={county} man={man} laws={laws} interps={interps} tech={tech} />}
  </>;
}

function Report({ facts, caseDate, county, man, laws, interps, tech }: { facts: string; caseDate: string | null; county: string; man: Manifest; laws: LawIdx[]; interps: InterpIdx[]; tech: TechIdx[] }) {
  const r = useMemo(() => build(facts, man, laws, interps, tech, caseDate, county), [facts, man, laws, interps, tech, caseDate, county]);
  const ci = countyInfo(man, county);
  return <div className="draft-box">
    <p className="small muted" style={{ marginTop: 0 }}>辨識到的主題：{r.matched.length ? r.matched.map((s) => <span key={s.id} className="tag neutral" style={{ marginRight: 4 }}>{s.title}</span>) : "（未辨識到特定主題，以下依事實文字檢索；可補充設施名稱、使用情形等描述）"}
      {r.factKeywords.length > 0 && <> ｜ 關鍵詞：{r.factKeywords.join("、")}</>}｜資料版本 {man.built_at.slice(0, 10)}</p>

    <h2>一、可能適用的法規條文 <TypeTag kind="law" /></h2>
    {!county && <p className="small muted">未選擇縣市：僅列出全國性法規。選擇縣市可一併列出該縣市地方規定。</p>}
    {county && !ci.checked && <div className="callout small" style={{ margin: "4px 0 8px" }}><strong>{county}：尚未查核</strong>。本站尚未收錄{county}之地方規定，請自行至該縣市法規查詢系統查詢；歡迎 <Link to="/sources#local">提供地方規定</Link>。</div>}
    {r.articles.length === 0 && <p className="muted small">未檢索到相關條文，請補充事實描述，或至 <Link to="/laws">法規</Link> 查詢。</p>}
    {r.articles.map(({ law, items, amendments }) => <div key={law.id} style={{ marginBottom: 10 }}>
      <strong><Link to={`/law/${law.id}`}>{law.n}</Link></strong> {law.cty && <LocalTag county={law.cty} />} <span className="small muted">（最新修正 {roc(law.md)}）</span>
      {amendments.length > 0 && <div className="callout small" style={{ margin: "4px 0" }}>案件日期 {roc(caseDate)} 之後，本法規曾修正 {amendments.length} 次：{amendments.slice(0, 4).map((a) => roc(a.date)).join("、")}。請確認案件適用之法規版本（施行日期以官方公告為準）。</div>}
      {items.length > 0
        ? <ul className="small">{items.map(([k, label, , t]) => <li key={k}><Link to={`/law/${law.id}#${articleAnchor(k)}`}>{label || articleName(k)}</Link>：{t.replace(/\s+/g, "").slice(0, 120)}…</li>)}</ul>
        : <p className="small muted">（未檢索到特定條文，請至法規頁查閱全文）</p>}
    </div>)}
    <p className="tiny muted">條文係依事實內容自收錄之官方條文檢索，可能有遺漏或不相關條文，請逐條確認適用條件；設施分類與面積請查官方附表。</p>

    <h2>二、協助判斷</h2>
    <h3>（一）待釐清事項</h3>
    <ul className="small">{r.openQuestions.map((f) => <li key={f}>{f}</li>)}</ul>

    <h3>（二）相關函釋 <TypeTag kind="interp" /></h3>
    {r.interps.length === 0 && <p className="muted small">未檢索到。可至 <Link to="/search?type=interp">函釋搜尋</Link> 調整關鍵字。</p>}
    <ol className="small">{r.interps.map(({ x, why }) => <li key={x.id} style={{ marginBottom: 6 }}>
      <Link to={`/interp/${x.id}`}>{x.ag || "（機關未載）"} {roc(x.d, true)} {x.no}</Link> <CourseTag fl={x.fl} /><ValidityTag status={x.v} />
      <div>{x.s}</div><div className="tiny muted">檢索理由：{why}。請比對函釋前提事實（設施種類、經營內容、程序階段）是否與本案相同。</div></li>)}</ol>
    {r.interpTotal > r.interps.length && <p className="small muted">另有 {r.interpTotal - r.interps.length} 件相關性較低之函釋，可至 <Link to="/search?type=interp">函釋搜尋</Link> 查詢。</p>}

    <h3>（三）注意事項</h3>
    <ul className="small">
      {r.cautions.map((c) => <li key={c}>{c}</li>)}
      <li>上列待釐清事項未查明前，無法確定是否符合法定要件，<strong>不宜作成准駁結論</strong>；有疑義時得函請上級主管機關釋示。</li>
      {r.interps.some((i) => i.x.v !== "no_known_cessation") && <li>部分函釋標示「{Array.from(new Set(r.interps.filter((i) => i.x.v !== "no_known_cessation").map((i) => VALIDITY_SHORT[i.x.v]))).join("、")}」，引用前應確認是否仍可援用。</li>}
      {r.interps.some((i) => i.x.fl.includes("course_summary")) && <li>標示「課程摘錄・非原文」之函釋僅為教育訓練資料之文字，引用前須先取得官方原文。</li>}
    </ul>

    {r.tech.length > 0 && <>
      <h3>（四）農業技術參考 <TypeTag kind="tech" /></h3>
      <p className="tiny muted">試驗研究機構出版品書目，僅供判斷農業經營合理性、設施需求之參考，不具法律效力。</p>
      <ul className="small">{r.tech.map((t) => <li key={t.id}><Link to={`/tech/${t.id}`}>{t.t}</Link>（{man.agency_names[t.ag] || t.ag}，{t.d ? roc(t.d) : "年月不詳"}）</li>)}</ul>
    </>}
  </div>;
}

interface Built {
  matched: Scenario[]; factKeywords: string[]; openQuestions: string[]; cautions: string[];
  articles: { law: LawIdx; items: LawIdx["a"]; amendments: { date: string; text: string }[] }[];
  interps: { x: InterpIdx; why: string }[]; interpTotal: number; tech: TechIdx[];
}

const uniq = <T,>(xs: T[]) => Array.from(new Set(xs));

/** 依事實文字判斷相關情境：情境之函釋主題關鍵字或觸發詞出現在事實中即視為相關 */
function matchScenarios(nf: string, man: Manifest, county: string): Scenario[] {
  const out = SCENARIOS.filter((s) => s.id !== "local" && uniq([...s.interpTopics.flatMap((t) => man.topics.legal_topics[t]?.keywords || []), ...(s.triggers || [])])
    .some((k) => k && nf.includes(norm(k))));
  const local = SCENARIOS.find((s) => s.id === "local");
  if (county && local) out.push(local);
  return out;
}

function build(facts: string, man: Manifest, laws: LawIdx[], interps: InterpIdx[], tech: TechIdx[], caseDate: string | null, county: string): Built {
  const nf = norm(facts);
  const factKeywords = uniq([...Object.values(man.topics.legal_topics).flatMap((t) => t.keywords), ...Object.values(man.topics.technical_topics).flatMap((t) => t.keywords)]
    .filter((k) => k.length >= 2 && nf.includes(norm(k)))).slice(0, 20);
  const matched = matchScenarios(nf, man, county);
  const byName = new Map(laws.map((l) => [l.n, l]));
  const lawKw = new Map<string, string[]>();
  for (const s of matched) for (const { law, keywords } of s.laws) lawKw.set(law, uniq([...(lawKw.get(law) || []), ...keywords]));
  const score = (l: LawIdx, kws: string[]) => l.a.map((a) => ({ a, s: kws.reduce((n, k) => n + (a[3].includes(k) ? 1 : 0), 0) }))
    .filter((x) => x.s > 0).sort((x, y) => y.s - x.s).slice(0, 6).map((x) => x.a);
  const articles: Built["articles"] = [];
  for (const [name, kws] of lawKw) {
    const l = byName.get(name);
    if (l) articles.push({ law: l, items: score(l, [...kws, ...factKeywords]), amendments: [] });
  }
  // 情境以外：事實關鍵詞在條文中出現 2 個以上之全國性法規，補列最多 4 部
  if (factKeywords.length) {
    const seen = new Set(articles.map((a) => a.law.id));
    laws.filter((l) => !l.cty && !seen.has(l.id)).map((l) => ({ l, items: score(l, factKeywords).filter((a) => factKeywords.filter((k) => a[3].includes(k)).length >= 2) }))
      .filter((x) => x.items.length).sort((a, b) => b.items.length - a.items.length).slice(0, 4)
      .forEach((x) => articles.push({ law: x.l, items: x.items, amendments: [] }));
  }
  // 地方規定：所選縣市中，管理者指定情境相符或主題相符者
  const ids = new Set(matched.map((s) => s.id));
  const topics = new Set(matched.flatMap((s) => s.interpTopics));
  const localKw = uniq([...lawKw.values()].flat().concat(factKeywords)).filter((k) => k.length >= 2);
  for (const l of laws.filter((x) => county && x.cty === county)) {
    const ok = l.scn && l.scn.length ? l.scn.some((s) => s !== "local" && ids.has(s)) : l.tp.some((t) => topics.has(t));
    if (ok) articles.push({ law: l, items: score(l, localKw), amendments: [] });
  }
  if (caseDate) for (const a of articles) a.amendments = (a.law.h || []).filter(([d, t]) => d > caseDate && !/權責事項|改由.{0,10}管轄/.test(t)).map(([date, text]) => ({ date, text }));

  const lawIds = new Set(articles.map((a) => a.law.id));
  const kws = uniq([...matched.flatMap((s) => s.interpKeywords), ...factKeywords]).map(norm);
  const scoredI = interps.map((x) => {
    let s = 0; const why: string[] = [];
    const tp = [...topics].filter((t) => x.tp.includes(t));
    if (tp.length) { s += 3 * tp.length; why.push("主題：" + tp.map((t) => man.topics.legal_topics[t]?.label).join("、")); }
    const subj = norm(x.s);
    const hits = kws.filter((k) => k && subj.includes(k));
    if (hits.length) { s += 2 * hits.length; why.push("主旨含「" + uniq(hits).join("、") + "」"); }
    if (x.rel.some(([l]) => lawIds.has(l))) s += 1;
    return { x, s, why: why.join("；") };
  }).filter((y) => y.s >= 3).sort((a, b) => b.s - a.s || (b.x.d || "").localeCompare(a.x.d || ""));

  const ttp = new Set(matched.flatMap((s) => s.techTopics));
  const techHits = tech.filter((t) => t.tp.some((p) => ttp.has(p)) || factKeywords.some((k) => t.t.includes(k)))
    .sort((a, b) => (b.d || "").localeCompare(a.d || "")).slice(0, 6);
  const openQuestions = uniq([...COMMON_FACTS, ...matched.flatMap((s) => s.facts)]);
  const cautions = uniq(matched.flatMap((s) => s.cautions));
  return { matched, factKeywords, openQuestions, cautions, articles, interps: scoredI.slice(0, 12), interpTotal: scoredI.length, tech: techHits };
}
