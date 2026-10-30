import { Link, useSearchParams } from "react-router-dom";
import { getLaws, getManifest } from "../lib/data";
import { CountySelect, countyInfo, LocalTag } from "../components/county";
import { roc } from "../lib/text";
import { ErrorBox, Loading, TypeTag, useAsync } from "../components/ui";
import type { LawIdx } from "../lib/types";

const TOPIC: Record<string, string> = { farm_use: "農地農用", facility: "容許使用", land_control: "土地使用管制", farmhouse: "農舍", soil_water: "水土保持／水利", tax: "稅務", procedure: "行政程序", building: "建築" };
const STATUS: Record<string, string> = { current: "現行", abolished: "已廢止", partially_pending: "部分條文尚未施行", needs_review: "尚待查核" };

export default function LawList() {
  const d = useAsync(() => Promise.all([getLaws(), getManifest()]), []);
  const [sp, setSp] = useSearchParams();
  if (d.error) return <ErrorBox msg={d.error} />;
  if (!d.data) return <Loading />;
  const [laws, man] = d.data;
  const county = sp.get("county") || "";
  const ci = countyInfo(man, county);
  const national = laws.filter((l) => !l.cty);
  const local = laws.filter((l) => county && l.cty === county);
  const groups: [string, LawIdx[]][] = [
    [`${county}地方規定（只適用於${county}）`, local],
    ["核心法規", national.filter((l) => l.core)],
    ["行政規則（審查要點等）", national.filter((l) => !l.core && l.lv === "行政規則")],
    ["相關交叉法規", national.filter((l) => !l.core && l.lv !== "行政規則")],
  ];
  return <>
    <h1>法規</h1>
    <p className="muted small">法律及命令以全國法規資料庫開放資料為主要來源；農地相關行政規則（審查要點等）取自農業部農村發展及水土保持署農地及農舍法規檢索系統。
      地方規定依縣市分開收錄，請選擇縣市查看；地方規定只適用於該縣市。</p>
    <div className="card row" style={{ marginBottom: 16 }}><strong>縣市地方規定</strong>
      <CountySelect man={man} value={county} onChange={(v) => setSp(v ? { county: v } : {}, { replace: true })} />
      {county && !ci.checked && <span className="small"><strong>{county}：尚未查核</strong>。本站尚未收錄{county}之地方規定，請至該縣市法規查詢系統查詢，或 <Link to="/sources#local">提供地方規定</Link>。</span>}
      {county && ci.checked && <span className="small muted">已收錄 {ci.laws} 部{ci.law_system && <>，來源：<a href={ci.law_system} target="_blank" rel="noopener noreferrer">{county}法規查詢系統 ↗</a></>}。收錄範圍為經管理者審核之農地相關規定，未收錄不代表不存在。</span>}
    </div>
    {groups.map(([title, list]) => list.length > 0 && <section key={title} className="card" style={{ marginBottom: 16 }}>
      <h2>{title}</h2>
      <div className="scroll-x"><table className="t">
        <thead><tr><th>法規名稱</th><th>類別</th><th>最新修正</th><th>狀態</th><th>條數</th><th>主題</th></tr></thead>
        <tbody>{list.map((l) => <tr key={l.id}>
          <td><Link to={`/law/${l.id}`}>{l.n}</Link> {l.cty && <LocalTag county={l.cty} />}</td>
          <td><TypeTag kind={l.lv === "行政規則" ? "rule" : "law"} /> <span className="small">{l.lv}</span></td>
          <td>{roc(l.md)}</td><td>{STATUS[l.st] || l.st}</td><td>{l.a.length}</td>
          <td className="small">{l.tp.map((t) => TOPIC[t] || t).join("、")}</td></tr>)}</tbody>
      </table></div>
    </section>)}
  </>;
}
