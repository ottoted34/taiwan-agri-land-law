import { diffChars } from "diff";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { getLaw, getVersion } from "../lib/data";
import { articleName, roc } from "../lib/text";
import type { LawVersion } from "../lib/types";
import { ErrorBox, Loading, useAsync } from "../components/ui";

export default function Compare() {
  const { id = "" } = useParams();
  const [sp, setSp] = useSearchParams();
  const law = useAsync(() => getLaw(id), [id]);
  const full = law.data?.versions.filter((v) => v.full) || [];
  const a = sp.get("a") || full[full.length - 2]?.id;
  const b = sp.get("b") || full[full.length - 1]?.id;
  const [vs, setVs] = useState<[LawVersion, LawVersion] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [onlyChanged, setOnlyChanged] = useState(true);
  useEffect(() => {
    if (!a || !b) return;
    setVs(null);
    Promise.all([getVersion(id, a), getVersion(id, b)]).then((x) => setVs(x as [LawVersion, LawVersion])).catch((e) => setErr(String(e.message)));
  }, [id, a, b]);
  const rows = useMemo(() => {
    if (!vs) return [];
    const [va, vb] = vs;
    const ma = new Map(va.articles.map((x) => [x.key, x.text]));
    const mb = new Map(vb.articles.map((x) => [x.key, x.text]));
    const keys = Array.from(new Set([...va.articles.map((x) => x.key), ...vb.articles.map((x) => x.key)]));
    keys.sort((x, y) => { const [a1, a2] = x.replace("P", "").split("-").map(Number); const [b1, b2] = y.replace("P", "").split("-").map(Number); return a1 - b1 || (a2 || 0) - (b2 || 0); });
    return keys.map((k) => {
      const ta = ma.get(k), tb = mb.get(k);
      const kind = ta == null ? "added" : tb == null ? "removed" : ta.replace(/\s/g, "") === tb.replace(/\s/g, "") ? "same" : "changed";
      return { k, ta, tb, kind };
    });
  }, [vs]);
  if (law.error || err) return <ErrorBox msg={law.error || err!} />;
  if (!law.data) return <Loading />;
  if (full.length < 2) return <div className="card"><h1>{law.data.name}－版本比較</h1><p>目前本站僅有 {full.length} 個全文版本，尚無法比較。本站會在法規每次修正時保存新版本快照。</p><Link to={`/law/${id}`}>回法規全文</Link></div>;
  const label = (v: { id: string; date: string | null; kind: string }) => `${roc(v.date)} ${v.kind === "captured" ? "（本站快照）" : "（官方歷史沿革）"}`;
  const stats = { changed: rows.filter((r) => r.kind === "changed").length, added: rows.filter((r) => r.kind === "added").length, removed: rows.filter((r) => r.kind === "removed").length };
  return <>
    <p><Link to={`/law/${id}`}>← {law.data.name}</Link></p>
    <h1>版本比較</h1>
    <div className="card row" style={{ marginBottom: 12 }}>
      <label>舊版本 <select value={a} onChange={(e) => setSp({ a: e.target.value, b: b! })}>{full.map((v) => <option key={v.id} value={v.id}>{label(v)}</option>)}</select></label>
      <label>新版本 <select value={b} onChange={(e) => setSp({ a: a!, b: e.target.value })}>{full.map((v) => <option key={v.id} value={v.id}>{label(v)}</option>)}</select></label>
      <label className="small"><input type="checkbox" checked={onlyChanged} onChange={(e) => setOnlyChanged(e.target.checked)} /> 只顯示有差異之條文</label>
    </div>
    {!vs ? <Loading what="版本" /> : <>
      <p className="small">修正（發布）日期：{roc(vs[0].modified_date, true)} → {roc(vs[1].modified_date, true)}。差異：修正 {stats.changed} 條、新增 {stats.added} 條、刪除 {stats.removed} 條。
        <span className="muted">施行日期依各版本沿革說明，請以官方公告為準。條號為各版本當時之條號，全文修正時條號可能已重新編排，逐條比對僅供參考。</span></p>
      <div className="card diff">
        {rows.filter((r) => !onlyChanged || r.kind !== "same").map((r) => <div key={r.k} className="article">
          <div className="no">{articleName(r.k)}<div className="tiny">{{ added: "新增", removed: "刪除", changed: "修正", same: "未變動" }[r.kind]}</div></div>
          <div className="doc">{r.kind === "added" ? <ins>{r.tb}</ins> : r.kind === "removed" ? <del>{r.ta}</del> : r.kind === "same" ? <span className="unchanged">{r.tb}</span> :
            diffChars(r.ta!, r.tb!).map((p, i) => p.added ? <ins key={i}>{p.value}</ins> : p.removed ? <del key={i}>{p.value}</del> : <span key={i}>{p.value}</span>)}</div>
        </div>)}
      </div>
      <p className="small muted">綠底為新增文字、紅底刪除線為刪除文字。</p>
    </>}
  </>;
}
