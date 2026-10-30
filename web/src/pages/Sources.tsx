import { Link } from "react-router-dom";
import { getManifest, getSources } from "../lib/data";
import { dt } from "../lib/text";
import { ErrorBox, ExtLink, Loading, Section, useAsync } from "../components/ui";

export const AUDIT: Record<string, [string, string]> = {
  synced_full: ["已完整盤點且可自動同步", "ok"], synced_partial: ["已盤點但只能部分同步", "part"], manual: ["已盤點且需人工補充", "part"],
  pending_license: ["已找到來源但尚未取得授權／robots 不允許", "part"], not_identified: ["尚未確認有適當資料來源", "fail"], discontinued: ["官方來源已停用", "fail"],
  unreachable: ["來源暫時無法連線", "fail"], no_relevant_data: ["經查核沒有與本專案相關的公開資料", ""],
};
/** 擁有者建立 Google 表單後填入網址（見 docs/google-form.md）；留空則不顯示 */
export const GOOGLE_FORM_URL = "https://forms.gle/UiC2xsxrAwgb5pns5";
const PRI = ["", "第一優先（核心）", "第二優先", "第三優先（特定業務）"];

export default function Sources() {
  const d = useAsync(() => Promise.all([getSources(), getManifest()]), []);
  if (d.error) return <ErrorBox msg={d.error} />;
  if (!d.data) return <Loading />;
  const [s, man] = d.data;
  return <>
    <h1>資料來源與更新狀態</h1>
    <div className="callout" style={{ marginBottom: 16 }}>「已同步」不代表該機關所有歷史文件均已收錄；「查無資料」不代表官方沒有相關資料。本站未虛構任何涵蓋率百分比。
      來源盤點於 {s.registry.last_reviewed} 人工確認，之後每月自動重新檢查連線與 robots 規則（最近一次：{dt(s.audit_checked_at)}）。</div>
    <Section title="地方規定（縣市）" right={<span id="local">{GOOGLE_FORM_URL ? <a className="btn small" href={GOOGLE_FORM_URL} target="_blank" rel="noopener noreferrer">提供地方規定 ↗</a>
      : <span className="small muted">提供管道建置中</span>}</span>}>
      <p className="small">地方自治法規、審查要點等地方規定<strong>依縣市分開收錄</strong>，只適用於該縣市。官方法規系統經確認 robots.txt 未限制擷取且資料可合法利用者才自動同步；
        其餘縣市顯示「尚未查核」。未收錄不代表該縣市沒有相關規定。</p>
      <div className="scroll-x"><table className="t"><thead><tr><th style={{ whiteSpace: "nowrap" }}>縣市</th><th>收錄數</th><th>同步方式</th><th>查核說明</th></tr></thead>
        <tbody>{(man.counties || []).filter((c) => c.checked).map((c) => <tr key={c.name}>
          <td style={{ whiteSpace: "nowrap" }}><span className="status-dot ok" /> <Link to={`/laws?county=${encodeURIComponent(c.name)}`}>{c.name}</Link></td><td>{c.laws}</td>
          <td className="small" style={{ whiteSpace: "nowrap" }}>{c.auto_sync ? <>自動同步{c.law_system && <><br /><ExtLink href={c.law_system}>官方法規系統</ExtLink></>}</> : "人工補充"}</td>
          <td className="tiny muted">{c.note}</td></tr>)}</tbody></table></div>
      <p className="small"><span className="status-dot" /> <strong>尚未查核</strong>：{(man.counties || []).filter((c) => !c.checked).map((c) => c.name).join("、")}</p>
      <h3>其他縣市同仁：歡迎提供地方規定</h3>
      <ol className="small">
        <li>{GOOGLE_FORM_URL ? "按右上「提供地方規定」填寫表單（不需帳號）" : "提供表單建置中，完成後會在本頁右上顯示「提供地方規定」按鈕"}：縣市、法規名稱、<strong>官方網址（必填）</strong>、發布或修正日期、施行日期、提供者單位（選填）。</li>
        <li>請只提供已公開之官方資料，<strong>勿填寫個人姓名、身分證字號、地號或個案資料</strong>。</li>
        <li>管理者至官方網址核對名稱、日期與全文後才會收錄。收錄不代表機關認可，網站仍以官方公告為準。</li>
      </ol>
      {s.local_candidates && Object.entries(s.local_candidates).map(([cty, v]) => v.candidates.length > 0 && <details key={cty} className="small">
        <summary>{cty}：系統自官方分類頁列出之待審核候選 {v.candidates.length} 筆（尚未收錄）</summary>
        <ul>{v.candidates.map((c) => <li key={c.law_system_id}><ExtLink href={c.url}>{c.name}</ExtLink>（{c.law_system_id}）</li>)}</ul></details>)}
    </Section>
    <Section title="來源登錄與盤點結果">
      <div className="scroll-x"><table className="t"><thead><tr><th>來源</th><th>機關</th><th>盤點狀態</th><th>內容／限制</th><th>每月檢查</th></tr></thead>
        <tbody>{s.registry.sources.map((x) => { const src = x as Record<string, string>; const [l, c] = AUDIT[src.audit_status] || [src.audit_status, ""]; const a = s.audit[src.id];
          return <tr key={src.id}><td>{src.url ? <ExtLink href={src.url}>{src.name}</ExtLink> : src.name}</td><td className="small">{src.agency}</td>
            <td><span className={`status-dot ${c}`} /> {l}</td><td className="small">{src.content}{src.note && <div className="muted">{src.note}</div>}{src.coverage && <div className="muted">涵蓋：{src.coverage}</div>}</td>
            <td className="small">{a ? <>{a.reachable === true ? "可連線" : a.reachable === false ? `無法連線${a.error ? "（" + a.error + "）" : ""}` : "未連線檢查"}{a.robots_allowed === false && "；robots 不允許"}<div className="tiny muted">{dt(a.checked_at)}</div></> : "—"}</td></tr>; })}</tbody></table></div>
    </Section>
    <Section title="農業部機關盤點與本站收錄筆數">
      <p className="small muted">依農業部「所屬機關(構)職掌」頁面建立名錄。筆數僅為本站收錄數，非機關資料總數。法規由法務部全國法規資料庫統一取得，不分機關計算。</p>
      <div className="scroll-x"><table className="t"><thead><tr><th>機關</th><th>層級</th><th>優先序</th><th>函釋</th><th>技術書目</th><th>備註</th></tr></thead>
        <tbody>{[...s.agencies].sort((a, b) => a.priority - b.priority).map((a) => <tr key={a.id}>
          <td>{a.official_site ? <ExtLink href={a.official_site}>{a.name}</ExtLink> : a.name}</td><td className="small">{a.level}</td><td className="small">{PRI[a.priority]}{a.relevance === "low" ? "（低相關）" : ""}</td>
          <td>{s.per_agency[a.id]?.interps ?? 0}</td><td>{s.per_agency[a.id]?.tech ?? 0}</td><td className="tiny muted">{a.note}</td></tr>)}</tbody></table></div>
    </Section>
    <Section title={`改制前機關對照（${s.historical.reorg_date} 行政院農業委員會改制為農業部）`}>
      <p className="small muted">本表為業務承接對照，<strong>不代表</strong>改制前機關發布之函釋當然繼續適用。</p>
      <table className="t"><thead><tr><th>改制前機關</th><th>現行業務承接機關</th><th>說明</th></tr></thead>
        <tbody>{s.historical.mappings.map((m) => <tr key={m.historical}><td>{m.historical}</td><td>{s.agencies.find((a) => a.id === m.successor)?.name || m.successor}</td><td className="small">{m.note}</td></tr>)}</tbody></table>
    </Section>
    {s.catalog && <Section title="農業資料開放平臺：自動搜尋到之出版品資料集">
      <p className="small muted">最近搜尋：{dt(s.catalog.discovered_at)}</p>
      <ul className="small">{s.catalog.datasets.map((c) => <li key={c.unit_id}>{c.title}（{c.organ}，代碼 {c.unit_id}）</li>)}</ul>
    </Section>}
    <p className="small muted">本站共收錄 {man.counts.laws} 部法規、{man.counts.interps} 件函釋、{man.counts.tech} 筆技術書目、{man.counts.law_versions} 個法規版本。</p>
  </>;
}
