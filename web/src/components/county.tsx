import type { County, Manifest } from "../lib/types";

/** 縣市選單：已查核之縣市排前面並標示收錄數；未查核者標示「尚未查核」。 */
export function CountySelect({ man, value, onChange, label = "縣市" }: { man: Manifest; value: string; onChange: (v: string) => void; label?: string }) {
  const cs = man.counties || [];
  return <label className="small">{label && <span className="sr-only">{label}</span>}
    <select value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}
      style={{ border: "1px solid var(--line-strong)", borderRadius: 6, padding: "3px 8px", background: "var(--surface)", color: "inherit" }}>
      <option value="">未選擇（僅全國性法規）</option>
      {cs.map((c) => <option key={c.name} value={c.name}>{c.name}{c.checked ? `（已收錄 ${c.laws} 部）` : "（尚未查核）"}</option>)}
    </select></label>;
}

export function countyInfo(man: Manifest, name: string): County {
  return (man.counties || []).find((c) => c.name === name) || { name, checked: false, laws: 0 };
}

export function LocalTag({ county }: { county: string }) {
  return <span className="tag warn" title="地方自治法規／地方行政規則，只適用於該縣市">{county}地方規定</span>;
}
