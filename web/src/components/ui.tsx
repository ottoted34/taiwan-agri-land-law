import { useEffect, useState, type ReactNode } from "react";
import { highlight } from "../lib/search";

export const DISCLAIMER = "本網站為非官方農業法規及技術資訊整理平台，並非農業部或其他政府機關官方網站。資料僅供檢索與研究參考，實際法律適用及行政處分仍應以主管機關現行正式資料與個案審認為準。";

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): { data: T | null; error: string | null } {
  const [state, set] = useState<{ data: T | null; error: string | null }>({ data: null, error: null });
  useEffect(() => {
    let live = true;
    set({ data: null, error: null });
    fn().then((d) => live && set({ data: d, error: null })).catch((e) => live && set({ data: null, error: String(e.message || e) }));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

export function Loading({ what = "資料" }: { what?: string }) { return <div className="loading" role="status">載入{what}中…</div>; }
export function ErrorBox({ msg }: { msg: string }) {
  return <div className="callout danger" role="alert">資料載入失敗：{msg}。請稍後重新整理。</div>;
}

export function Hl({ text, terms, max }: { text: string; terms: string[][]; max?: number }) {
  return <>{highlight(text, terms, max).map(([t, m], i) => (m ? <mark key={i}>{t}</mark> : <span key={i}>{t}</span>))}</>;
}

export function TypeTag({ kind }: { kind: "law" | "interp" | "tech" | "rule" }) {
  if (kind === "law") return <span className="tag law">法規條文</span>;
  if (kind === "rule") return <span className="tag law">行政規則</span>;
  if (kind === "interp") return <span className="tag interp">函釋</span>;
  return <span className="tag tech" title="農業技術參考資料，不具法律效力">技術參考資料</span>;
}

const VALIDITY_CLASS: Record<string, string> = {
  no_known_cessation: "neutral", ceased: "danger", revoked: "danger", amended_by_later: "warn", possibly_affected: "warn", needs_review: "warn",
};
export const VALIDITY_SHORT: Record<string, string> = {
  no_known_cessation: "未查得停止適用", ceased: "官方停止適用", revoked: "官方廢止／撤回", amended_by_later: "後續函釋補充變更",
  possibly_affected: "可能受修法影響", needs_review: "效力待查核",
};
export function ValidityTag({ status, confirmed }: { status: string; confirmed?: boolean }) {
  return <span className={`tag ${VALIDITY_CLASS[status] || "neutral"}`} title="系統依已收錄官方資料比對之結果，非效力認定">
    {VALIDITY_SHORT[status] || status}{confirmed === false && status !== "no_known_cessation" ? "（系統比對）" : ""}{confirmed ? "（人工確認）" : ""}
  </span>;
}

/** 課程摘錄（教育訓練資料之文字，非函釋原文） */
export const COURSE_FLAG = "course_summary";
export function CourseTag({ fl }: { fl?: string[] }) {
  return fl && fl.includes(COURSE_FLAG) ? <span className="tag warn" title="摘自農業部所屬機關教育訓練資料，非函釋原文；引用前請取得官方原文">課程摘錄・非原文</span> : null;
}

export function CopyButton({ text, label = "複製" }: { text: string; label?: string }) {
  const [ok, setOk] = useState(false);
  return <button className="btn ghost small no-print" onClick={async () => {
    try { await navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 1600); }
    catch { window.prompt("請手動複製：", text); }
  }}>{ok ? "已複製 ✓" : label}</button>;
}

export function Section({ title, children, right }: { title: ReactNode; children: ReactNode; right?: ReactNode }) {
  return <section className="card" style={{ marginBottom: 16 }}>
    <div className="row" style={{ marginBottom: 8 }}><h2 style={{ margin: 0 }}>{title}</h2><div className="spacer" />{right}</div>
    {children}
  </section>;
}

export function ExtLink({ href, children }: { href: string; children: ReactNode }) {
  return <a href={href} target="_blank" rel="noopener noreferrer">{children} <span aria-hidden>↗</span><span className="sr-only">（另開新視窗）</span></a>;
}

export function Pager({ page, total, size, onPage }: { page: number; total: number; size: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size));
  if (pages <= 1) return null;
  const nums = Array.from(new Set([1, page - 2, page - 1, page, page + 1, page + 2, pages])).filter((p) => p >= 1 && p <= pages).sort((a, b) => a - b);
  return <nav className="pager" aria-label="分頁">
    <button className="btn ghost small" disabled={page <= 1} onClick={() => onPage(page - 1)}>上一頁</button>
    {nums.map((p) => <button key={p} className={`btn small ${p === page ? "" : "ghost"}`} aria-current={p === page} onClick={() => onPage(p)}>{p}</button>)}
    <button className="btn ghost small" disabled={page >= pages} onClick={() => onPage(page + 1)}>下一頁</button>
  </nav>;
}
