import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getInterps, getLaws, getManifest, getTech } from "../lib/data";
import { dt, roc } from "../lib/text";
import { DISCLAIMER, ErrorBox, Loading, TypeTag, useAsync, ValidityTag } from "../components/ui";

const QUICK = ["資材室", "農機具室", "溫室", "網室", "鋪設水泥", "填土", "貨櫃", "農用證明", "部分面積", "果樹", "集貨", "農路"];
const RESULT_LABEL: Record<string, string> = {
  success_changed: "已成功檢查，有資料異動", success_no_change: "已成功檢查、無資料異動", partial_failure: "部分來源檢查失敗", failed: "檢查失敗",
};

export default function Home() {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const m = useAsync(getManifest, []);
  const extra = useAsync(() => Promise.all([getInterps(), getLaws(), getTech()]), []);
  const go = (s: string) => nav(`/search?q=${encodeURIComponent(s)}`);
  const man = m.data;
  return <>
    <section className="hero">
      <h1>臺灣農地農用及農業設施容許使用<br />法規、函釋暨農業技術知識平台</h1>
      <p className="muted" style={{ marginTop: 0 }}>整合全國法規資料庫、農業部農村發展及水土保持署函釋系統、農業資料開放平臺之公開資料。可依法規名稱、條號、發文字號、日期（民國或西元）、關鍵字查詢。</p>
      <form role="search" onSubmit={(e) => { e.preventDefault(); go(q); }}>
        <label htmlFor="q" className="sr-only">搜尋</label>
        <div className="searchbox">
          <input id="q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="例：資材室、農保規字第1150230515號、農業發展條例第8條之1、115/7/28" autoFocus />
          <button className="btn" type="submit">搜尋</button>
        </div>
      </form>
      <div className="chips" style={{ marginTop: 10 }}>{QUICK.map((k) => <button key={k} className="chip" onClick={() => go(k)}>{k}</button>)}</div>
    </section>

    <div className="callout" style={{ margin: "16px 0" }}>{DISCLAIMER}</div>

    {m.error && <ErrorBox msg={m.error} />}
    {!man && !m.error && <Loading />}
    {man && <>
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Link to="/laws" className="card stat" style={{ textDecoration: "none", color: "inherit" }}><b>{man.counts.laws}</b><span>部法規（{man.counts.articles.toLocaleString()} 條／點）</span></Link>
        <Link to="/search?type=interp" className="card stat" style={{ textDecoration: "none", color: "inherit" }}><b>{man.counts.interps.toLocaleString()}</b><span>件函釋</span></Link>
        <Link to="/search?type=tech" className="card stat" style={{ textDecoration: "none", color: "inherit" }}><b>{man.counts.tech.toLocaleString()}</b><span>筆農業技術書目</span></Link>
        <Link to="/updates" className="card stat" style={{ textDecoration: "none", color: "inherit" }}><b style={{ fontSize: "1rem", paddingTop: 6 }}>{dt(man.last_success_any)}</b><span>最後成功同步（臺灣時間）</span></Link>
      </div>
      {man.latest_run && <p className="small muted">最近一次更新作業：{dt(man.latest_run.started_at)}（{man.latest_run.mode}）— {RESULT_LABEL[man.latest_run.result] || man.latest_run.result}。<Link to="/updates">查看更新紀錄</Link></p>}

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <section className="card">
          <h2>農地農用認定</h2>
          <p className="small muted">農業用地作農業使用認定、農用證明核發、部分面積農業使用、鋪面與填土等。</p>
          <div className="chips">
            {[["法規：認定及核發證明辦法", "/search?type=law&q=" + encodeURIComponent("農業用地作農業使用認定及核發證明辦法")],
              ["函釋：農用證明", "/search?type=interp&topic=farm_use_cert"], ["函釋：部分面積", "/search?type=interp&topic=partial_use"],
              ["函釋：鋪面", "/search?type=interp&topic=paving"], ["函釋：填土堆置", "/search?type=interp&topic=landfill"]].map(([l, h]) => <Link key={h} className="chip" to={h}>{l}</Link>)}
          </div>
        </section>
        <section className="card">
          <h2>農業設施容許使用</h2>
          <p className="small muted">申請農業用地作農業設施容許使用審查辦法、附表、經營計畫、設施使用管理等。</p>
          <div className="chips">
            {[["審查辦法全文", "/law/M0020022"], ["函釋：資材室", "/search?type=interp&topic=material_room"], ["函釋：農機具室", "/search?type=interp&topic=machinery_room"],
              ["函釋：溫網室", "/search?type=interp&topic=greenhouse"], ["函釋：使用管理", "/search?type=interp&topic=facility_use"], ["案件審查輔助", "/assist"]].map(([l, h]) => <Link key={h} className="chip" to={h}>{l}</Link>)}
          </div>
        </section>
      </div>

      {extra.data && (() => {
        const [its, laws, techs] = extra.data;
        const ib = new Map(its.map((i) => [i.id, i]));
        const lb = new Map(laws.map((l) => [l.id, l]));
        const tb = new Map(techs.map((t) => [t.id, t]));
        return <div className="grid cols-3">
          <section className="card"><h2>最新函釋</h2>
            {man.latest.interps.map((id) => ib.get(id)).filter(Boolean).map((r) => <div key={r!.id} className="result">
              <div className="meta"><TypeTag kind="interp" /><span>{roc(r!.d)}</span><ValidityTag status={r!.v} /></div>
              <h3><Link to={`/interp/${r!.id}`}>{r!.s}</Link></h3><div className="tiny muted">{r!.no}</div></div>)}
            <Link to="/search?type=interp&sort=date">更多函釋 →</Link></section>
          <section className="card"><h2>最新法規異動</h2>
            {man.latest.laws.map((id) => lb.get(id)).filter(Boolean).map((l) => <div key={l!.id} className="result">
              <div className="meta"><TypeTag kind={l!.lv === "行政規則" ? "rule" : "law"} /><span>修正 {roc(l!.md)}</span></div>
              <h3><Link to={`/law/${l!.id}`}>{l!.n}</Link></h3></div>)}
            <Link to="/laws">全部法規 →</Link></section>
          <section className="card"><h2>最新農業技術資料</h2>
            {man.latest.tech.map((id) => tb.get(id)).filter(Boolean).map((t) => <div key={t!.id} className="result">
              <div className="meta"><TypeTag kind="tech" /><span>{t!.d ? roc(t!.d) : ""}</span><span>{man.agency_names[t!.ag] || t!.ag}</span></div>
              <h3><Link to={`/tech/${t!.id}`}>{t!.t}</Link></h3></div>)}
            {man.counts.tech === 0 && <p className="muted small">尚未同步，請見 <Link to="/sources">資料來源狀態</Link>。</p>}
            <Link to="/search?type=tech&sort=date">更多技術資料 →</Link></section>
        </div>;
      })()}
    </>}
  </>;
}
