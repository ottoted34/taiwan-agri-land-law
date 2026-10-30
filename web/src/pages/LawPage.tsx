import { LocalTag } from "../components/county";
import { useEffect, useMemo } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { getInterps, getLaw } from "../lib/data";
import { articleAnchor, articleName, dt, letterDate, roc } from "../lib/text";
import { CopyButton, CourseTag, ErrorBox, ExtLink, Loading, Section, TypeTag, useAsync, ValidityTag } from "../components/ui";

const STATUS: Record<string, string> = { current: "現行有效", abolished: "已廢止", partially_pending: "有已公布尚未施行之規定", needs_review: "尚待查核" };
const SRC: Record<string, string> = { "moj-law-api": "全國法規資料庫開放資料", "rmis-laws": "農地及農舍法規檢索系統" };

export default function LawPage() {
  const { id = "" } = useParams();
  const loc = useLocation();
  const d = useAsync(() => Promise.all([getLaw(id), getInterps()]), [id]);
  useEffect(() => {
    if (d.data && loc.hash) document.getElementById(loc.hash.slice(1))?.scrollIntoView();
  }, [d.data, loc.hash]);
  const related = useMemo(() => {
    if (!d.data) return null;
    const [, its] = d.data;
    const byArt = new Map<string, typeof its>();
    const lawLevel: typeof its = [];
    for (const r of its) for (const [l, a, k] of r.rel) {
      if (l !== id) continue;
      if (a) { if (!byArt.has(a)) byArt.set(a, []); if (!byArt.get(a)!.includes(r)) byArt.get(a)!.push(r); }
      else if (k === "official" && !lawLevel.includes(r)) lawLevel.push(r);
    }
    return { byArt, lawLevel };
  }, [d.data, id]);
  if (d.error) return <ErrorBox msg={d.error} />;
  if (!d.data || !related) return <Loading what="法規" />;
  const [law] = d.data;
  let lastChapter: string | null = null;
  const cite = `${law.name}（${roc(law.modified_date, true)}修正）`;
  const fullVersions = law.versions.filter((v) => v.full);

  return <div className="layout-detail">
    <article>
      <div className="row"><TypeTag kind={law.level === "行政規則" ? "rule" : "law"} />{law.county && <LocalTag county={law.county} />}<span className="small muted">{law.level}｜{law.category}</span></div>
      {law.county && <div className="callout small" style={{ margin: "8px 0" }}>本法規為<strong>{law.county}</strong>地方規定，只適用於{law.county}轄區案件。
        {law.published_date && <> 公發布日 {roc(law.published_date, true)}。</>}{law.docno_text && <> 最新發文字號：{law.docno_text}。</>}
        {law.review && <> 收錄審核：{law.review.reviewed_by || "—"}（{law.review.reviewed_at || "—"}）{law.review.issue && <>，<a href={law.review.issue} target="_blank" rel="noopener noreferrer">審核紀錄 ↗</a></>}。</>}</div>}
      <h1>{law.name}</h1>
      <dl className="kv card" style={{ marginBottom: 16 }}>
        <dt>狀態</dt><dd>{STATUS[law.status] || law.status}{law.effective_note && <div className="small">施行說明：{law.effective_note}</div>}{law.abandon_note && <div className="small">廢止：{law.abandon_note}</div>}</dd>
        <dt>最新修正（發布）日期</dt><dd>{roc(law.modified_date, true)}（{law.modified_date || "—"}）{law.effective_date && <>；施行日期 {roc(law.effective_date, true)}</>}</dd>
        <dt>官方來源</dt><dd><ExtLink href={law.official_url}>{SRC[law.primary_source] || "官方網站"}</ExtLink>{law.rmis && law.primary_source !== "rmis-laws" && <> ・ <ExtLink href={law.rmis.url}>農地及農舍法規檢索系統</ExtLink></>}</dd>
        <dt>本站最後查核</dt><dd>{dt(law.last_checked)}（內容最後異動 {dt(law.last_changed)}）</dd>
        {law.former_names && law.former_names.length > 0 && <><dt>原名稱</dt><dd>{law.former_names.join("、")}</dd></>}
      </dl>
      {law.flags?.includes("rmis_newer") && <div className="callout" style={{ marginBottom: 12 }}>農地及農舍法規檢索系統標示之修正日期（{roc(law.rmis?.modified_date)}）晚於全國法規資料庫（{roc(law.modified_date)}），可能尚未同步，請以官方公告為準。</div>}
      {law.cross_check && law.cross_check.text_differs.length > 0 && <div className="callout info small" style={{ marginBottom: 12 }}>兩官方來源條文文字比對有差異之條號：{law.cross_check.text_differs.slice(0, 20).join("、")}（多為標點、編號格式差異；本頁以 {SRC[law.primary_source]} 為準）。</div>}
      <div className="row no-print" style={{ marginBottom: 10 }}>
        <CopyButton text={cite} label="複製引用" />
        {fullVersions.length >= 2 && <Link className="btn ghost small" to={`/law/${law.id}/compare`}>版本比較</Link>}
        <button className="btn ghost small" onClick={() => window.print()}>列印</button>
      </div>
      {law.foreword && <p className="doc">{law.foreword}</p>}
      <section className="card">
        {law.articles.map((a) => {
          const ch = a.chapter && a.chapter !== lastChapter ? a.chapter : null;
          if (ch) lastChapter = ch;
          const rel = related.byArt.get(a.key) || [];
          return <div key={a.key}>
            {ch && <div className="chapter">{ch}</div>}
            <div className="article" id={articleAnchor(a.key)}>
              <div className="no"><a href={`#${articleAnchor(a.key)}`} onClick={(e) => { e.preventDefault(); history.replaceState(null, "", `#/law/${law.id}#${articleAnchor(a.key)}`); document.getElementById(articleAnchor(a.key))?.scrollIntoView(); }}>{a.label || articleName(a.key)}</a></div>
              <div>
                <div className="doc">{a.text}</div>
                {rel.length > 0 && <details className="small no-print" style={{ marginTop: 6 }}>
                  <summary>引用本條之函釋 {rel.length} 件（系統由函釋內文比對，非官方關聯）</summary>
                  <ul>{rel.sort((x, y) => (y.d || "").localeCompare(x.d || "")).slice(0, 30).map((r) => <li key={r.id}><Link to={`/interp/${r.id}`}>{letterDate(r.d, r.yh)} {r.no}</Link> {r.s.slice(0, 60)}… <CourseTag fl={r.fl} /><ValidityTag status={r.v} /></li>)}</ul>
                  <Link to={`/search?type=interp&law=${law.id}&q=${encodeURIComponent(articleName(a.key).replace(/\s/g, ""))}`}>搜尋更多</Link>
                </details>}
              </div>
            </div>
          </div>;
        })}
      </section>
      {law.attachments.length > 0 && <Section title="附表／附件">
        <ul>{law.attachments.map((a, i) => <li key={i}>{a.url ? <ExtLink href={a.url}>{a.name}</ExtLink> : a.name}</li>)}</ul>
        <p className="small muted">附表檔案連結至官方網站，本站未複製檔案內容。設施分類、面積及條件請以官方附表為準。</p>
      </Section>}
      <Section title="修正沿革">
        <ol className="small">{law.histories.map((h, i) => <li key={i}>{h.text}</li>)}</ol>
      </Section>
      {law.versions.length > 0 && <Section title="已收錄版本" right={fullVersions.length >= 2 ? <Link className="btn small" to={`/law/${law.id}/compare`}>比較版本</Link> : undefined}>
        <table className="t"><thead><tr><th>日期</th><th>類型</th><th>說明</th></tr></thead><tbody>
          {law.versions.map((v) => <tr key={v.id}><td>{roc(v.date)}</td><td>{v.kind === "captured" ? "本站擷取現行條文快照" : "官方歷史沿革"}{v.full ? "（全文）" : "（僅修正說明）"}</td>
            <td className="small">{v.url ? <ExtLink href={v.url}>{v.entry || "原始頁面"}</ExtLink> : v.entry}</td></tr>)}
        </tbody></table>
        <p className="small muted">本站自開始收錄日起保存每次修正之現行條文快照；更早之版本僅收錄官方系統提供全文之歷史沿革。</p>
      </Section>}
    </article>
    <aside className="no-print">
      <div className="card">
        <strong>條文目錄</strong>
        <nav className="toc" aria-label="條文目錄">{law.articles.map((a) => <a key={a.key} href={`#/law/${law.id}#${articleAnchor(a.key)}`}>{a.label || articleName(a.key)}{related.byArt.get(a.key) ? ` ・函釋${related.byArt.get(a.key)!.length}` : ""}</a>)}</nav>
      </div>
      {related.lawLevel.length > 0 && <div className="card" style={{ marginTop: 12 }}>
        <strong>官方列示之相關函釋</strong>
        <p className="small muted">農地及農舍法規檢索系統「解釋內容」依本法規列示 {related.lawLevel.length} 件。</p>
        <Link className="btn small" to={`/search?type=interp&law=${law.id}&sort=date`}>查看全部</Link>
      </div>}
    </aside>
  </div>;
}
