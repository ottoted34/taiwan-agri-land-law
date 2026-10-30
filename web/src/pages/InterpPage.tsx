import { Link, useParams } from "react-router-dom";
import { getInterp, getManifest } from "../lib/data";
import { articleAnchor, articleName, dt, letterDate, roc } from "../lib/text";
import { CopyButton, COURSE_FLAG, CourseTag, ErrorBox, ExtLink, Loading, Section, TypeTag, useAsync, ValidityTag } from "../components/ui";

const SOURCE_NAME: Record<string, string> = {
  "rmis-interpretations": "農地及農舍法規檢索系統（函釋明細）", "rmis-lawexp": "農地及農舍法規檢索系統（法規對應解釋函頁）",
  "forest-interpretations": "林業及自然保育署（公文函釋）", "talis-green-energy": "農業綠能發展資訊網（函釋查詢）",
  "course-summaries": "教育訓練資料摘錄（無官方原文連結）",
};

const KIND: Record<string, string> = { official: "官方列示", extracted: "系統比對（演算法建議）", manual: "人工確認" };

export default function InterpPage() {
  const { id = "" } = useParams();
  const d = useAsync(() => Promise.all([getInterp(id), getManifest()]), [id]);
  if (d.error) return <ErrorBox msg={d.error} />;
  if (!d.data) return <Loading what="函釋" />;
  const [r, man] = d.data;
  const cite = `${r.agency_text || r.historical_name || ""}${roc(r.date, true)}${r.docno}${r.category === "解釋令" ? "令" : "函"}`;
  const v = r.validity;
  const rels = [...r.relations].sort((a, b) => ["manual", "official", "extracted"].indexOf(a.kind) - ["manual", "official", "extracted"].indexOf(b.kind));
  return <div className="layout-detail">
    <article>
      <div className="row"><TypeTag kind="interp" />{r.category && <span className="tag neutral">{r.category}</span>}<ValidityTag status={v.status} confirmed={v.confirmed} />
        {r.is_historical && <span className="tag neutral">改制前機關</span>}<CourseTag fl={r.flags} /></div>
      <h1 style={{ marginTop: 8 }}>{r.subject}</h1>
      <dl className="kv card" style={{ marginBottom: 16 }}>
        <dt>發文機關</dt><dd>{r.agency_text || "（原始資料未載）"}{r.historical_name && r.agency_name && <div className="small muted">改制前機關：{r.historical_name}；目前業務承接機關（業務對照，非效力認定）：{r.agency_name}</div>}</dd>
        <dt>發文日期</dt><dd>{r.date ? <>{roc(r.date, true)}（{r.date}）</> : <>{letterDate(null, r.year_hint)}<div className="small muted">本筆僅見於官方「法規對應解釋函」頁面，該頁未提供發文日期；推估年度僅供排序，請查官方原文。</div></>}</dd>
        <dt>發文字號</dt><dd className="row">{r.docno} <CopyButton text={r.docno} label="複製字號" /> <CopyButton text={cite} label="複製引用" /></dd>
        <dt>官方原文</dt><dd>{r.sources.map((s) => <div key={s.source_key}>{s.url ? <ExtLink href={s.url}>{SOURCE_NAME[s.source_id] || s.source_id}</ExtLink> : SOURCE_NAME[s.source_id] || s.source_id} <span className="tiny muted">擷取 {dt(s.fetched_at)}</span></div>)}</dd>
        <dt>最後確認</dt><dd>{dt(r.last_synced)}（首次收錄 {dt(r.first_seen)}；內容版本 {r.version}）</dd>
      </dl>
      {r.flags.includes(COURSE_FLAG) && <div className="callout danger" style={{ marginBottom: 12 }}><strong>本筆為課程摘錄，不是函釋原文。</strong>
        內容摘自農業部所屬機關教育訓練資料（見下方備註），可能是摘要或其他函釋之引述；本站尚未取得官方原文。請勿逕予引用，應先向發文機關取得原文核對字號、日期與全文。</div>}
      {r.source_missing_since && <div className="callout danger" style={{ marginBottom: 12 }}>官方來源自 {dt(r.source_missing_since)} 起已查無此筆，可能已下架、搬移或停止適用，請向主管機關確認。本站保留歷史紀錄供查考。</div>}
      <ValidityBox v={v} man={man.validity_labels} lawNames={man.law_names} />
      <Section title="內容">
        <div className="doc">{r.content || "（官方系統未提供內容）"}</div>
        {r.memo && <p className="small"><strong>備註：</strong>{r.memo}</p>}
        <p className="small muted">{r.flags.includes(COURSE_FLAG) ? "內容為教育訓練資料之文字轉錄，非函釋原文。" : "內容係官方系統公開文字之轉錄；如原文含附件，請至官方原文頁面查閱。"}</p>
      </Section>
      {r.history && r.history.length > 0 && <Section title="本站偵測之官方內容異動">
        <ul className="small">{r.history.map((h, i) => <li key={i}>{dt(h.at)}：異動欄位 {h.changed_fields.join("、")}</li>)}</ul>
      </Section>}
    </article>
    <aside>
      <div className="card">
        <strong>相關法規及條文</strong>
        {rels.length === 0 && <p className="small muted">尚無關聯資料。</p>}
        <ul className="small" style={{ paddingLeft: 18 }}>{rels.map((x, i) => <li key={i}>
          <Link to={`/law/${x.law_id}${x.article ? "#" + articleAnchor(x.article) : ""}`}>{man.law_names[x.law_id] || x.law_id}{x.article ? " " + articleName(x.article) : ""}</Link>
          <div className="tiny muted">{KIND[x.kind]}{x.evidence && <> ・<a href={x.evidence} target="_blank" rel="noopener noreferrer">依據</a></>}</div></li>)}</ul>
        <p className="tiny muted">「系統比對」係依函釋文字出現之法規名稱與條號自動建立，僅供查找，不代表法律適用關係。</p>
      </div>
      {r.topics.length > 0 && <div className="card" style={{ marginTop: 12 }}><strong>業務主題（系統自動標記）</strong>
        <div className="chips" style={{ marginTop: 6 }}>{r.topics.map((t) => <Link key={t} className="chip" to={`/search?type=interp&topic=${t}`}>{man.topics.legal_topics[t]?.label || t}</Link>)}</div></div>}
    </aside>
  </div>;
}

function ValidityBox({ v, man, lawNames }: { v: { status: string; confirmed: boolean; basis: Record<string, unknown>[]; notes?: string[] }; man: Record<string, string>; lawNames: Record<string, string> }) {
  const cls = v.status === "no_known_cessation" ? "info" : v.status === "ceased" || v.status === "revoked" ? "danger" : "";
  return <div className={`callout ${cls}`} style={{ marginBottom: 16 }}>
    <strong>效力查核資訊：{man[v.status] || v.status}</strong>{v.confirmed ? "（人工確認）" : "（系統依已收錄資料比對，未經人工確認）"}
    {v.status === "no_known_cessation" && <p className="small" style={{ margin: "4px 0 0" }}>僅表示本站已收錄之官方資料中，尚未查得停止適用或變更資訊；<strong>不代表本函釋目前仍有效</strong>，引用前請查證現行法規與後續函釋。</p>}
    {v.basis.length > 0 && <ul className="small" style={{ margin: "6px 0 0" }}>{v.basis.slice(0, 10).map((b, i) => <li key={i}>
      {b.type === "law_amendment" && <>所涉 <Link to={`/law/${b.law_id}${b.article ? "#" + articleAnchor(String(b.article)) : ""}`}>{lawNames[String(b.law_id)] || String(b.law_name)}{b.article ? " " + articleName(String(b.article)) : ""}</Link> 於 {roc(String(b.amended_on), true)} 修正（{String(b.history)}），晚於本函發文日，適用前請確認修正內容。</>}
      {b.type === "cessation_signal" && <>後續文件 <Link to={`/interp/${b.by_id}`}>{String(b.by_docno)}（{roc(String(b.by_date))}）</Link> 提及停止／不再適用本函：「{String(b.phrase).slice(0, 120)}」</>}
      {b.type === "amend_signal" && <>後續文件 <Link to={`/interp/${b.by_id}`}>{String(b.by_docno)}（{roc(String(b.by_date))}）</Link> 可能補充或變更本函：「{String(b.phrase).slice(0, 120)}」</>}
      {b.type === "manual" && <>人工查核：{String(b.text || "")} {b.evidence ? <a href={String(b.evidence)} target="_blank" rel="noopener noreferrer">依據</a> : null}</>}
    </li>)}</ul>}
    {v.notes?.map((n) => <p key={n} className="small" style={{ margin: "4px 0 0" }}>{n}</p>)}
  </div>;
}
