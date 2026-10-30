/** Text helpers: normalisation for matching only — displayed text is always the official text. */
const FW = "０１２３４５６７８９";
export function norm(s: string): string {
  return (s || "")
    .normalize("NFKC")
    .replace(/[０-９]/g, (c) => String(FW.indexOf(c)))
    .replace(/\s+/g, "")
    .toLowerCase();
}

export function rocToIso(t: string): string | null {
  const s = t.normalize("NFKC");
  let m = s.match(/^(?:民國)?(\d{2,3})[年/.\-](\d{1,2})[月/.\-](\d{1,2})日?$/);
  if (m) return iso(+m[1] + 1911, +m[2], +m[3]);
  m = s.match(/^(19|20)(\d{2})[-/.](\d{1,2})[-/.](\d{1,2})$/);
  if (m) return iso(+(m[1] + m[2]), +m[3], +m[4]);
  return null;
}
function iso(y: number, m: number, d: number) {
  const dt = new Date(Date.UTC(y, m - 1, d));
  if (dt.getUTCMonth() !== m - 1) return null;
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

/** "2026-07-28" -> "115/07/28" */
export function roc(isoDate: string | null | undefined, withLabel = false): string {
  if (!isoDate) return "日期不詳";
  const [y, m, d] = isoDate.slice(0, 10).split("-");
  const r = `${+y - 1911}/${m}${d ? "/" + d : ""}`;
  return withLabel ? `民國${r}` : r;
}
export function dt(isoTs: string | null | undefined): string {
  if (!isoTs) return "—";
  const d = new Date(isoTs);
  if (isNaN(+d)) return isoTs;
  return d.toLocaleString("zh-TW", { timeZone: "Asia/Taipei", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
}

const CN = "零一二三四五六七八九";
export function cnToInt(s: string): number | null {
  if (/^\d+$/.test(s)) return +s;
  let total = 0, num = 0;
  const units: Record<string, number> = { 十: 10, 百: 100, 千: 1000 };
  for (const ch of s) {
    const i = CN.indexOf(ch === "〇" ? "零" : ch);
    if (i >= 0) num = i;
    else if (units[ch]) { total += (num || 1) * units[ch]; num = 0; }
    else return null;
  }
  return total + num;
}

/** Parse "第8條之1" / "第 8-1 條" / "8-1" -> "8-1" */
export function articleKey(q: string): string | null {
  const s = q.normalize("NFKC").replace(/\s/g, "");
  const m = s.match(/第?([0-9一二三四五六七八九十百零〇]+)(?:[-之]([0-9一二三四五六七八九十]+))?條(?:之([0-9一二三四五六七八九十]+))?/);
  if (!m) return null;
  const a = cnToInt(m[1]);
  const sub = m[2] || m[3];
  if (a == null) return null;
  const b = sub ? cnToInt(sub) : null;
  return b ? `${a}-${b}` : String(a);
}
export function articleAnchor(key: string) { return "a-" + key; }
export function articleName(key: string) { return key.startsWith("P") ? `第 ${key.slice(1)} 點` : `第 ${key} 條`; }

export function docnoKey(s: string) {
  return norm(s).replace(/號.*$/, "號");
}

/** Display date for letters; undated ones show the docno-based estimate, clearly labelled. */
export function letterDate(d: string | null | undefined, yh?: number | null): string {
  if (d) return roc(d);
  return yh ? `日期未載（依字號推估約民國${yh - 1911}年）` : "官方頁面未載日期";
}
