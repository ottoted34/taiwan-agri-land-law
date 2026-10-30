import { getManifest, getSources } from "../lib/data";
import { dt } from "../lib/text";
import { ErrorBox, ExtLink, Loading, Section, useAsync } from "../components/ui";
import { SRC_NAME, SRC_STATUS } from "./Updates";

export const AUDIT: Record<string, [string, string]> = {
  synced_full: ["已完整盤點且可自動同步", "ok"], synced_partial: ["已盤點但只能部分同步", "part"], manual: ["已盤點且需人工補充", "part"],
  pending_license: ["已找到來源但尚未取得授權／robots 不允許", "part"], not_identified: ["尚未確認有適當資料來源", "fail"], discontinued: ["官方來源已停用", "fail"],
  unreachable: ["來源暫時無法連線", "fail"], no_relevant_data: ["經查核沒有與本專案相關的公開資料", ""],
};
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
    <Section title="自動同步來源狀態">
      <div className="scroll-x"><table className="t"><thead><tr><th>來源</th><th>最近檢查</th><th>結果</th><th>最近成功同步</th><th>最近完整比對</th><th>最近資料異動</th></tr></thead>
        <tbody>{Object.entries(s.status).map(([id, st]) => { const [l, c] = SRC_STATUS[st.last_status || ""] || [st.last_status, ""]; return <tr key={id}>
          <td>{SRC_NAME[id] || id}</td><td>{dt(st.last_checked)}</td><td><span className={`status-dot ${c}`} /> {l}{st.last_errors && st.last_errors.length > 0 && <div className="tiny" style={{ color: "var(--danger)" }}>{st.last_errors[0].slice(0, 120)}</div>}</td>
          <td>{dt(st.last_success)}</td><td>{dt(st.last_full_compare)}</td><td>{dt(st.last_changed)}</td></tr>; })}</tbody></table></div>
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
