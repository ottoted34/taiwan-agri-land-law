import { Link, useParams } from "react-router-dom";
import { getManifest, getTech } from "../lib/data";
import { dt, roc } from "../lib/text";
import { ErrorBox, ExtLink, Loading, TypeTag, useAsync } from "../components/ui";

export default function TechPage() {
  const { id = "" } = useParams();
  const d = useAsync(() => Promise.all([getTech(), getManifest()]), [id]);
  if (d.error) return <ErrorBox msg={d.error} />;
  if (!d.data) return <Loading />;
  const [all, man] = d.data;
  const t = all.find((x) => x.id === id);
  if (!t) return <div className="card"><h1>查無此筆技術資料</h1><Link to="/search?type=tech">回技術資料搜尋</Link></div>;
  return <article style={{ maxWidth: 860 }}>
    <div className="row"><TypeTag kind="tech" /><span className="small muted">{t.se}</span></div>
    <h1 style={{ marginTop: 8 }}>{t.t}</h1>
    <div className="callout tech" style={{ marginBottom: 16 }}><strong>技術參考資料</strong>：本筆為試驗研究機構出版品之書目資訊，可作為農業經營合理性、設施需求或現況判斷之專業參考，
      <strong>不具法規或函釋效力</strong>，亦不能據以推論農業設施容許使用或農用證明之准駁。</div>
    {t.miss && <div className="callout danger" style={{ marginBottom: 12 }}>此筆自 {dt(t.miss)} 起已不在官方資料集中，可能已更正或下架。</div>}
    <dl className="kv card">
      <dt>發布機關</dt><dd>{man.agency_names[t.ag] || t.ag}</dd>
      <dt>刊物／編號</dt><dd>{t.se} {t.is}</dd>
      {t.au && <><dt>作者</dt><dd>{t.au}</dd></>}
      <dt>出版年月</dt><dd>{t.d ? `${roc(t.d, true)}（${t.d}）` : "未載"}</dd>
      {t.pg && <><dt>頁數</dt><dd>{t.pg}</dd></>}
      {t.isbn && <><dt>ISBN</dt><dd>{t.isbn}</dd></>}
      {t.gpn && <><dt>GPN</dt><dd>{t.gpn}</dd></>}
      <dt>技術主題（系統自動標記）</dt><dd>{t.tp.length ? t.tp.map((x) => man.topics.technical_topics[x]?.label || x).join("、") : "—"}</dd>
      <dt>原始官方網址</dt><dd>{t.u ? <ExtLink href={t.u}>開啟官方檔案或頁面</ExtLink> : "官方資料未提供連結"}</dd>
      <dt>書目來源</dt><dd>{t.dsu ? <ExtLink href={t.dsu}>{t.ds || "農業資料開放平臺"}</ExtLink> : t.ds}</dd>
      <dt>資料授權</dt><dd className="small">{t.lic}</dd>
      <dt>最後查核</dt><dd>{dt(t.ls)}</dd>
    </dl>
    <p className="small muted">本站僅收錄書目與官方連結，未複製出版品全文。相關法規及函釋請以 <Link to={`/search?q=${encodeURIComponent(t.t.slice(0, 6))}`}>關鍵字搜尋</Link> 另行查找。</p>
  </article>;
}
