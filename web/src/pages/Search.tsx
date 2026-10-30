import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getInterps, getLaws, getManifest, getTech } from "../lib/data";
import { parseQuery, prepInterps, prepLaws, prepTech, searchArticles, searchInterps, searchTech } from "../lib/search";
import type { ParsedQuery } from "../lib/search";
import { articleAnchor, letterDate, roc, rocToIso } from "../lib/text";
import type { Manifest } from "../lib/types";
import { CopyButton, ErrorBox, Hl, Loading, Pager, TypeTag, useAsync, VALIDITY_SHORT, ValidityTag } from "../components/ui";

type Tab = "all" | "law" | "interp" | "tech";
const SIZE = 20;
const FACILITY_WORDS = ["資材", "農機具", "溫室", "網室", "集貨", "育苗", "菇", "農路", "灌溉", "倉庫", "冷藏", "乾燥", "畜", "禽", "養殖", "綠能", "管理室", "設施"];
const ALL_AGENCIES_INTERP = ["ardswc", "moa", "afa", "forest"];

let prepared: { laws: ReturnType<typeof prepLaws>; interps: ReturnType<typeof prepInterps>; tech: ReturnType<typeof prepTech>; man: Manifest } | null = null;
async function loadAll() {
  if (prepared) return prepared;
  const [man, laws, interps, tech] = await Promise.all([getManifest(), getLaws(), getInterps(), getTech()]);
  prepared = { man, laws: prepLaws(laws), interps: prepInterps(interps), tech: prepTech(tech) };
  return prepared;
}

export default function SearchPage() {
  const [sp, setSp] = useSearchParams();
  const d = useAsync(loadAll, []);
  const q = sp.get("q") || "";
  const tab = (sp.get("type") as Tab) || "all";
  const page = Number(sp.get("page") || 1);
  const sort = sp.get("sort") || "relevance";
  const set = (k: string, v: string | null) => { const n = new URLSearchParams(sp); if (v) n.set(k, v); else n.delete(k); if (k !== "page") n.delete("page"); setSp(n); };
  const [input, setInput] = useState(q);

  const res = useMemo(() => {
    if (!d.data) return null;
    const { man, laws, interps, tech } = d.data;
    const pq = parseQuery(q, man.synonyms, man.law_names);
    const from = rocToIso(sp.get("from") || "") || (sp.get("from") ? undefined : undefined);
    const to = rocToIso(sp.get("to") || "") || undefined;
    const iHits = searchInterps(interps, pq, { agency: sp.get("agency") || undefined, from: from || undefined, to, topic: sp.get("topic") || undefined,
      validity: sp.get("validity") || undefined, law: sp.get("law") || undefined, historical: (sp.get("hist") as "only" | "exclude") || undefined });
    const aHits = (sp.get("topic") || sp.get("validity") || sp.get("agency") || sp.get("hist") || sp.get("from") || sp.get("to")) && tab !== "law" ? [] :
      searchArticles(laws, pq, sp.get("law") || undefined);
    const tHits = sp.get("validity") || sp.get("law") || sp.get("hist") ? [] : searchTech(tech, pq, { agency: sp.get("agency") || undefined, topic: sp.get("ttopic") || undefined });
    const byDate = <T,>(arr: T[], get: (x: T) => string | null) => [...arr].sort((a, b) => (get(b) || "").localeCompare(get(a) || ""));
    const bySc = <T extends { score: number },>(arr: T[], get: (x: T) => string | null) => [...arr].sort((a, b) => b.score - a.score || (get(b) || "").localeCompare(get(a) || ""));
    return {
      pq, man,
      interps: sort === "date" || !q ? byDate(iHits, (x) => x.r.d || (x.r.yh ? `${x.r.yh}-00` : null)) : bySc(iHits, (x) => x.r.d || (x.r.yh ? `${x.r.yh}-00` : null)),
      arts: bySc(aHits, (x) => x.a.law.md),
      tech: sort === "date" || !q ? byDate(tHits, (x) => x.r.d) : bySc(tHits, (x) => x.r.d),
    };
  }, [d.data, q, sp, tab, sort]);

  if (d.error) return <ErrorBox msg={d.error} />;
  if (!d.data || !res) return <Loading what="搜尋索引" />;
  const { man, pq } = res;
  const counts = { law: res.arts.length, interp: res.interps.length, tech: res.tech.length };
  const showLaw = tab === "all" || tab === "law", showInterp = tab === "all" || tab === "interp", showTech = tab === "all" || tab === "tech";

  return <>
    <form role="search" onSubmit={(e) => { e.preventDefault(); set("q", input.trim() || null); }} style={{ marginBottom: 12 }}>
      <div className="searchbox">
        <label htmlFor="sq" className="sr-only">搜尋</label>
        <input id="sq" value={input} onChange={(e) => setInput(e.target.value)} placeholder="關鍵字、發文字號、法規名稱＋條號、日期（115/7/28）" />
        <button className="btn">搜尋</button>
      </div>
    </form>
    <QueryInfo pq={pq} man={man} />
    <div className="layout-search">
      <aside className="card filters" aria-label="篩選條件">
        <strong>篩選</strong>
        <label htmlFor="f-law">相關法規</label>
        <select id="f-law" value={sp.get("law") || ""} onChange={(e) => set("law", e.target.value || null)}>
          <option value="">不限</option>{Object.entries(man.law_names).map(([id, n]) => <option key={id} value={id}>{n}</option>)}
        </select>
        <label htmlFor="f-ag">來源機關</label>
        <select id="f-ag" value={sp.get("agency") || ""} onChange={(e) => set("agency", e.target.value || null)}>
          <option value="">不限</option>{Object.entries(man.agency_names).map(([id, n]) => <option key={id} value={id}>{n}{ALL_AGENCIES_INTERP.includes(id) ? "" : ""}</option>)}
        </select>
        <label htmlFor="f-from">發布期間（民國或西元）</label>
        <div className="row" style={{ flexWrap: "nowrap" }}>
          <input id="f-from" placeholder="起 例 105/1/1" defaultValue={sp.get("from") || ""} onBlur={(e) => set("from", e.target.value.trim() || null)} />
          <input aria-label="迄" placeholder="迄" defaultValue={sp.get("to") || ""} onBlur={(e) => set("to", e.target.value.trim() || null)} />
        </div>
        <label htmlFor="f-tp">函釋業務主題（系統自動標記）</label>
        <select id="f-tp" value={sp.get("topic") || ""} onChange={(e) => set("topic", e.target.value || null)}>
          <option value="">不限</option>{Object.entries(man.topics.legal_topics).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <label htmlFor="f-v">函釋效力查核資訊</label>
        <select id="f-v" value={sp.get("validity") || ""} onChange={(e) => set("validity", e.target.value || null)}>
          <option value="">不限</option>{Object.entries(VALIDITY_SHORT).map(([k, v]) => <option key={k} value={k}>{v}（{man.validity_counts[k] || 0}）</option>)}
        </select>
        <label htmlFor="f-h">改制前（112/8/1 前）文件</label>
        <select id="f-h" value={sp.get("hist") || ""} onChange={(e) => set("hist", e.target.value || null)}>
          <option value="">不限</option><option value="only">僅改制前機關</option><option value="exclude">排除改制前機關</option>
        </select>
        <label htmlFor="f-tt">技術主題（系統自動標記）</label>
        <select id="f-tt" value={sp.get("ttopic") || ""} onChange={(e) => set("ttopic", e.target.value || null)}>
          <option value="">不限</option>{Object.entries(man.topics.technical_topics).map(([k, v]) => <option key={k} value={k}>{v.group}－{v.label}</option>)}
        </select>
        <label htmlFor="f-s">排序</label>
        <select id="f-s" value={sort} onChange={(e) => set("sort", e.target.value === "relevance" ? null : e.target.value)}>
          <option value="relevance">相關性</option><option value="date">日期（新到舊）</option>
        </select>
        <p style={{ marginTop: 12 }}><Link to="/search" className="small">清除所有條件</Link></p>
      </aside>
      <section>
        <div className="tabs" role="tablist">
          {([["all", "全部"], ["law", `法規條文 ${counts.law}`], ["interp", `函釋 ${counts.interp}`], ["tech", `技術資料 ${counts.tech}`]] as [Tab, string][]).map(([k, l]) =>
            <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => set("type", k === "all" ? null : k)}>{l}</button>)}
        </div>
        {counts.law + counts.interp + counts.tech === 0 && <NoResults q={q} />}
        {showLaw && res.arts.length === 0 && pq.terms.length > 0 && FACILITY_WORDS.some((w) => q.includes(w)) && <div className="callout info small" style={{ marginBottom: 10 }}>
          農業設施之種類、名稱、面積與條件多規定於「申請農業用地作農業設施容許使用審查辦法」<strong>附表一至附表五</strong>（官方 PDF），條文本文不一定出現設施名稱。
          請至 <Link to="/law/M0020022">審查辦法</Link> 頁面下方「附表／附件」開啟官方附表查閱。</div>}
        {tab === "all" && <p className="small muted">搜尋結果僅表示文字相符，不代表該文件直接適用於個案。函釋、技術資料與法規條文分別標示。</p>}
        {showLaw && res.arts.length > 0 && <ResultBlock title="法規條文" total={res.arts.length} more={tab === "all" ? () => set("type", "law") : undefined}>
          {(tab === "all" ? res.arts.slice(0, 5) : res.arts.slice((page - 1) * SIZE, page * SIZE)).map(({ a }) =>
            <div key={a.law.id + a.key} className="result">
              <div className="meta"><TypeTag kind={a.law.lv === "行政規則" ? "rule" : "law"} /><span>{a.law.n}</span>{a.chapter && <span>{a.chapter}</span>}<span>修正 {roc(a.law.md)}</span></div>
              <h3><Link to={`/law/${a.law.id}#${articleAnchor(a.key)}`}>{a.law.n} {a.label}</Link></h3>
              <div className="snip"><Hl text={a.text} terms={pq.terms} /></div>
            </div>)}
          {tab === "law" && <Pager page={page} total={res.arts.length} size={SIZE} onPage={(p) => set("page", String(p))} />}
        </ResultBlock>}
        {showInterp && res.interps.length > 0 && <ResultBlock title="函釋" total={res.interps.length} more={tab === "all" ? () => set("type", "interp") : undefined}>
          {(tab === "all" ? res.interps.slice(0, 8) : res.interps.slice((page - 1) * SIZE, page * SIZE)).map(({ r }) =>
            <div key={r.id} className="result">
              <div className="meta"><TypeTag kind="interp" /><span>{letterDate(r.d, r.yh)}</span><span>{r.ag || "（未載機關）"}</span>{r.h && <span className="tag neutral">改制前</span>}<ValidityTag status={r.v} />
                {r.cat && r.cat !== "解釋函" && <span className="tag neutral">{r.cat}</span>}</div>
              <h3><Link to={`/interp/${r.id}`}><Hl text={r.s || "（無主旨）"} terms={pq.terms} max={300} /></Link></h3>
              <div className="row tiny muted"><span>{r.no}</span><CopyButton text={r.no} label="複製字號" /></div>
              {pq.terms.length > 0 && <div className="snip"><Hl text={r.c} terms={pq.terms} /></div>}
            </div>)}
          {tab === "interp" && <Pager page={page} total={res.interps.length} size={SIZE} onPage={(p) => set("page", String(p))} />}
        </ResultBlock>}
        {showTech && res.tech.length > 0 && <ResultBlock title="農業技術參考資料" total={res.tech.length} more={tab === "all" ? () => set("type", "tech") : undefined}>
          <div className="callout tech small">技術參考資料僅供農業經營合理性與設施需求之專業參考，<strong>不具法規或函釋效力</strong>，不能據以推論准駁。</div>
          {(tab === "all" ? res.tech.slice(0, 5) : res.tech.slice((page - 1) * SIZE, page * SIZE)).map(({ r }) =>
            <div key={r.id} className="result">
              <div className="meta"><TypeTag kind="tech" /><span>{man.agency_names[r.ag] || r.ag}</span><span>{r.se} {r.is}</span>{r.d && <span>{roc(r.d)}</span>}</div>
              <h3><Link to={`/tech/${r.id}`}><Hl text={r.t} terms={pq.terms} max={200} /></Link></h3>
              {r.au && <div className="tiny muted">{r.au}</div>}
            </div>)}
          {tab === "tech" && <Pager page={page} total={res.tech.length} size={SIZE} onPage={(p) => set("page", String(p))} />}
        </ResultBlock>}
      </section>
    </div>
  </>;
}

function ResultBlock({ title, total, more, children }: { title: string; total: number; more?: () => void; children: React.ReactNode }) {
  return <div className="card" style={{ marginBottom: 14 }}>
    <div className="row"><h2 style={{ margin: 0 }}>{title}</h2><span className="muted small">共 {total.toLocaleString()} 筆</span><div className="spacer" />
      {more && total > 0 && <button className="btn ghost small" onClick={more}>只看{title} →</button>}</div>
    {children}
  </div>;
}

function QueryInfo({ pq, man }: { pq: ParsedQuery; man: Manifest }) {
  const bits: string[] = [];
  if (pq.docno) bits.push(`發文字號：${pq.docno}`);
  if (pq.date) bits.push(`日期：${roc(pq.date, true)}（${pq.date}）`);
  if (pq.lawHint) bits.push(`法規：${man.law_names[pq.lawHint]}`);
  if (pq.article) bits.push(`條號：${pq.article.startsWith("P") ? pq.article : "第 " + pq.article + " 條"}`);
  pq.terms.forEach((g) => bits.push(g.length > 1 ? `「${g[0]}」（含同義詞：${g.slice(1).join("、")}）` : `「${g[0]}」`));
  if (!bits.length) return null;
  return <p className="small muted">查詢解析：{bits.join("；")}</p>;
}

function NoResults({ q }: { q: string }) {
  return <div className="card"><h2>查無符合資料</h2>
    <ul className="small">
      <li>改用較短或較通用的詞，例如「資材」而非「農業資材室申請」。</li>
      <li>多個詞以空白分隔時須全部符合，可刪減詞彙。</li>
      <li>發文字號請輸入完整字號，如「農保規字第1150230515號」，或僅輸入數字部分。</li>
      <li>條號查詢請同時輸入法規名稱，如「農業發展條例第8條之1」。</li>
      <li>查無資料不代表官方無相關規定；本站收錄範圍見 <Link to="/sources">資料來源</Link>。</li>
    </ul>
    {q && <p className="small">也可至官方系統查詢：<a href="https://rmis.ardswc.gov.tw/Web/Search.aspx" target="_blank" rel="noopener noreferrer">農地及農舍法規檢索系統</a>、<a href="https://law.moj.gov.tw/" target="_blank" rel="noopener noreferrer">全國法規資料庫</a>。</p>}
  </div>;
}
