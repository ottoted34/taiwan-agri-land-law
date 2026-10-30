import { Link } from "react-router-dom";
import { getUpdates } from "../lib/data";
import { dt } from "../lib/text";
import { ErrorBox, Loading, useAsync } from "../components/ui";

export const RESULT: Record<string, [string, string]> = {
  success_changed: ["已成功檢查，有資料異動", "ok"], success_no_change: ["已成功檢查、無資料異動", "ok"],
  partial_failure: ["部分來源檢查失敗", "part"], failed: ["檢查失敗", "fail"], no_sources: ["未執行任何來源", "part"],
};
export const SRC_STATUS: Record<string, [string, string]> = {
  ok: ["成功", "ok"], partial: ["部分成功", "part"], failed: ["檢查失敗", "fail"], quarantined: ["異常已隔離", "fail"],
  robots_disallowed: ["robots 不允許", "part"], unavailable: ["無法連線", "fail"],
};
const MODE: Record<string, string> = { daily: "每日更新", weekly: "每週完整比對", technical: "技術資料更新", monthly: "每月來源盤點", full: "完整重建" };
const SRC_NAME: Record<string, string> = { "moj-law-api": "全國法規資料庫", "rmis-interpretations": "農地及農舍法規檢索系統－函釋", "rmis-laws": "農地及農舍法規檢索系統－法規",
  "rmis-lawexp": "農地及農舍法規檢索系統－法規對應函釋", "datamoa-publications": "農業資料開放平臺－出版品", "source-audit": "來源盤點", "local-taichung": "臺中市法規查詢系統（地方規定）" };
export { SRC_NAME };

export default function Updates() {
  const d = useAsync(getUpdates, []);
  if (d.error) return <ErrorBox msg={d.error} />;
  if (!d.data) return <Loading what="更新紀錄" />;
  return <>
    <h1>更新紀錄</h1>
    <p className="small muted">每日臺灣時間 03:20 檢查法規與函釋；每週日完整比對；每週四更新農業技術資料；每月 1 日盤點所有來源。以下列出最近 60 次作業。
      完整紀錄見 <a href="https://github.com/ottoted34/taiwan-agri-land-law/tree/main/data/updates" target="_blank" rel="noopener noreferrer">GitHub data/updates</a>。</p>
    {d.data.length === 0 && <p>尚無紀錄。</p>}
    {d.data.map((r) => {
      const [label, cls] = RESULT[r.result] || [r.result, ""];
      return <details key={r.run_id + r.started_at} className="card" style={{ marginBottom: 10 }} open={r === d.data![0]}>
        <summary className="row"><span className={`status-dot ${cls}`} /> <strong>{dt(r.started_at)}</strong> <span>{MODE[r.mode] || r.mode}</span> <span className="muted">— {label}</span></summary>
        <div className="scroll-x" style={{ marginTop: 8 }}><table className="t">
          <thead><tr><th>來源</th><th>結果</th><th>新增</th><th>修正</th><th>狀態變更</th><th>拒收</th><th>失敗</th><th>來源已查無</th><th>請求數</th></tr></thead>
          <tbody>{r.sources.map((s) => { const [sl, sc] = SRC_STATUS[s.status] || [s.status, ""]; return <tr key={s.source_id}>
            <td>{SRC_NAME[s.source_id] || s.source_id}{!s.complete && <div className="tiny muted">本次為部分範圍檢查</div>}</td>
            <td><span className={`status-dot ${sc}`} /> {sl}</td><td>{s.added}</td><td>{s.modified}</td><td>{s.status_changed}</td><td>{s.rejected}</td><td>{s.failed}</td><td>{s.missing_flagged}</td><td>{s.requests}</td></tr>; })}</tbody>
        </table></div>
        {r.sources.some((s) => s.errors.length || s.notes.length) && <ul className="small">{r.sources.flatMap((s) => [
          ...s.notes.map((n, i) => <li key={s.source_id + "n" + i} className="muted">{SRC_NAME[s.source_id] || s.source_id}：{n}</li>),
          ...s.errors.slice(0, 5).map((e, i) => <li key={s.source_id + "e" + i} style={{ color: "var(--danger)" }}>{SRC_NAME[s.source_id] || s.source_id}：{e}</li>)])}</ul>}
        {r.events.length > 0 && <details className="small"><summary>異動明細（{r.events.length}）</summary><ul>{r.events.slice(0, 100).map((e, i) => <li key={i}>
          {e.kind === "added" && <>新增{e.type === "law" ? "法規" : "函釋"}：{e.type === "law" ? <Link to={`/law/${e.id}`}>{String(e.name)}</Link> : <Link to={`/interp/${e.id}`}>{String(e.docno)}</Link>}</>}
          {e.kind === "modified" && <>內容修正：<Link to={`/interp/${e.id}`}>{String(e.docno)}</Link></>}
          {e.kind === "law_amended" && <>法規修正：<Link to={`/law/${e.id}`}>{String(e.name)}</Link>（條號 {(e.articles as string[]).join("、")}）</>}
          {e.kind === "missing_from_source" && <>官方來源已查無：<Link to={`/interp/${e.id}`}>{String(e.source_key)}</Link></>}
          {e.kind === "quarantine" && <>隔離：{String(e.source)} — {String(e.reason)}</>}
          {e.kind === "history_version" && <>收錄歷史版本：<Link to={`/law/${e.law_id}`}>{String(e.law_id)}</Link> {String(e.version)}</>}
          {e.kind === "identity_conflict" && <>字號身分衝突待查：{String(e.docno)}</>}
        </li>)}</ul></details>}
      </details>;
    })}
  </>;
}
