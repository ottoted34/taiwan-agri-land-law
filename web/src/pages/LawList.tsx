import { Link } from "react-router-dom";
import { getLaws } from "../lib/data";
import { roc } from "../lib/text";
import { ErrorBox, Loading, TypeTag, useAsync } from "../components/ui";

const TOPIC: Record<string, string> = { farm_use: "農地農用", facility: "容許使用", land_control: "土地使用管制", farmhouse: "農舍", soil_water: "水土保持／水利", tax: "稅務", procedure: "行政程序", building: "建築" };
const STATUS: Record<string, string> = { current: "現行", abolished: "已廢止", partially_pending: "部分條文尚未施行", needs_review: "尚待查核" };

export default function LawList() {
  const d = useAsync(getLaws, []);
  if (d.error) return <ErrorBox msg={d.error} />;
  if (!d.data) return <Loading />;
  const groups: [string, typeof d.data][] = [
    ["核心法規", d.data.filter((l) => l.core)],
    ["行政規則（審查要點等）", d.data.filter((l) => !l.core && l.lv === "行政規則")],
    ["相關交叉法規", d.data.filter((l) => !l.core && l.lv !== "行政規則")],
  ];
  return <>
    <h1>法規</h1>
    <p className="muted small">法律及命令以全國法規資料庫開放資料為主要來源；農地相關行政規則（審查要點等）取自農業部農村發展及水土保持署農地及農舍法規檢索系統。地方自治法規模組已建置資料結構，尚未完成查核。</p>
    {groups.map(([title, list]) => list.length > 0 && <section key={title} className="card" style={{ marginBottom: 16 }}>
      <h2>{title}</h2>
      <div className="scroll-x"><table className="t">
        <thead><tr><th>法規名稱</th><th>類別</th><th>最新修正</th><th>狀態</th><th>條數</th><th>主題</th></tr></thead>
        <tbody>{list.map((l) => <tr key={l.id}>
          <td><Link to={`/law/${l.id}`}>{l.n}</Link></td>
          <td><TypeTag kind={l.lv === "行政規則" ? "rule" : "law"} /> <span className="small">{l.lv}</span></td>
          <td>{roc(l.md)}</td><td>{STATUS[l.st] || l.st}</td><td>{l.a.length}</td>
          <td className="small">{l.tp.map((t) => TOPIC[t] || t).join("、")}</td></tr>)}</tbody>
      </table></div>
    </section>)}
  </>;
}
