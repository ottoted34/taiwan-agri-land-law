/**
 * Search engine. Chinese text is matched by normalised substring (no word segmentation needed,
 * so 專有名詞 like「資材室」are never split). Each whitespace-separated term must match (AND),
 * after synonym expansion. 發文字號 and 條號 are recognised and matched exactly.
 */
import type { InterpIdx, LawIdx, TechIdx } from "./types";
import { articleKey, docnoKey, norm, rocToIso } from "./text";

export interface ParsedQuery {
  raw: string;
  terms: string[][];          // AND of OR-groups (synonyms)
  docno: string | null;       // normalised 字號 when the query looks like one
  date: string | null;        // ISO date if the query contains a ROC/AD date
  article: string | null;     // "8-1"
  lawHint: string | null;     // law id mentioned in the query
}

export function parseQuery(raw: string, synonyms: string[][], lawNames: Record<string, string>): ParsedQuery {
  let q = raw.normalize("NFKC").trim();
  let docno: string | null = null;
  const dm = q.match(/([一-鿿]{1,8}字)\s*第\s*([0-9A-Za-z\-]+)\s*號/);
  if (dm) { docno = docnoKey(`${dm[1]}第${dm[2]}號`); q = q.replace(dm[0], " "); }
  else {
    const bare = q.match(/^\s*([0-9]{7,12}[A-Za-z]?)\s*$/);  // digits only, e.g. 1150230515
    if (bare) docno = bare[1].toLowerCase();
  }
  let date: string | null = null;
  for (const tok of q.split(/\s+/)) { const d = rocToIso(tok); if (d) { date = d; q = q.replace(tok, " "); break; } }
  let lawHint: string | null = null;
  const names = Object.entries(lawNames).sort((a, b) => b[1].length - a[1].length);
  for (const [id, name] of names) { if (q.includes(name)) { lawHint = id; q = q.replace(name, " "); break; } }
  let article: string | null = null;
  const am = q.match(/第?\s*[0-9一二三四五六七八九十百]+\s*(?:[-之]\s*[0-9一二三四五六七八九十]+)?\s*條(?:之[0-9一二三四五六七八九十]+)?/);
  if (am) { article = articleKey(am[0]); q = q.replace(am[0], " "); }
  const terms = q.split(/\s+/).map((t) => t.replace(/[「」『』《》""'']/g, "")).filter((t) => t.length > 0).map((t) => {
    const n = norm(t);
    const group = synonyms.find((g) => g.some((s) => norm(s) === n));
    return Array.from(new Set([n, ...(group ? group.map(norm) : [])]));
  });
  return { raw, terms, docno, date, article, lawHint };
}

const countIn = (hay: string, needle: string, cap = 5) => {
  let n = 0, i = 0;
  while (n < cap && (i = hay.indexOf(needle, i)) >= 0) { n++; i += needle.length; }
  return n;
};

/** score a document; fields ordered by weight. Returns 0 when a term is missing. */
function scoreFields(fields: [string, number][], terms: string[][]): number {
  let total = 0;
  for (const group of terms) {
    let best = 0;
    for (const variant of group) {
      let s = 0;
      for (const [text, w] of fields) s += countIn(text, variant) * w * (variant === group[0] ? 1 : 0.8);
      best = Math.max(best, s);
    }
    if (best === 0) return 0;
    total += best;
  }
  return total;
}

// ---- prepared (normalised) corpora, built once per dataset
export interface PreparedInterp { r: InterpIdx; no: string; s: string; c: string; ag: string }
export function prepInterps(rows: InterpIdx[]): PreparedInterp[] {
  return rows.map((r) => ({ r, no: docnoKey(r.no), s: norm(r.s), c: norm(r.c), ag: norm(r.ag) }));
}
export interface PreparedArticle { law: LawIdx; key: string; label: string; chapter: string | null; text: string; t: string; n: string }
export function prepLaws(rows: LawIdx[]): PreparedArticle[] {
  const out: PreparedArticle[] = [];
  for (const law of rows) for (const [key, label, chapter, text] of law.a)
    out.push({ law, key, label: label || key, chapter, text, t: norm(text), n: norm(law.n) });
  return out;
}
export interface PreparedTech { r: TechIdx; t: string; x: string }
export function prepTech(rows: TechIdx[]): PreparedTech[] {
  return rows.map((r) => ({ r, t: norm(r.t), x: norm([r.se, r.au, r.is, r.ds, r.ab || ""].join(" ")) }));
}

/** normalised textual forms of an article number, e.g. "29-1" -> 第29條之1 / 第29-1條 / 第29之1條 */
export function articlePatterns(key: string): string[] {
  const [a, b] = key.split("-");
  if (!b) return [norm(`第${a}條`)];
  return [norm(`第${a}條之${b}`), norm(`第${a}-${b}條`), norm(`第${a}之${b}條`)];
}

export interface InterpFilter { agency?: string; from?: string; to?: string; topic?: string; validity?: string; law?: string; historical?: "only" | "exclude" }

export function searchInterps(data: PreparedInterp[], q: ParsedQuery, f: InterpFilter = {}) {
  const hits: { r: InterpIdx; score: number }[] = [];
  for (const p of data) {
    const r = p.r;
    if (f.agency && r.agid !== f.agency) continue;
    if (f.from && (!r.d || r.d < f.from)) continue;
    if (f.to && (!r.d || r.d > f.to)) continue;
    if (f.topic && !r.tp.includes(f.topic)) continue;
    if (f.validity && r.v !== f.validity) continue;
    if (f.historical === "only" && !r.h) continue;
    if (f.historical === "exclude" && r.h) continue;
    const lawFilter = f.law || q.lawHint;
    if (lawFilter && !r.rel.some(([l, a]) => l === lawFilter && (!q.article || a === q.article))) {
      if (!(q.article && r.rel.some(([l]) => l === lawFilter) && articlePatterns(q.article).some((pat) => p.c.includes(pat) || p.s.includes(pat)))) continue;
    } else if (!lawFilter && q.article && !r.rel.some(([, a]) => a === q.article)) continue;
    let score = 1;
    if (q.docno) {
      if (p.no === q.docno) score += 1000;
      else if (p.no.includes(q.docno)) score += 500;
      else continue;
    }
    if (q.date) { if (r.d === q.date) score += 50; else continue; }
    if (q.terms.length) {
      const s = scoreFields([[p.s, 6], [p.no, 6], [p.ag, 2], [p.c, 1]], q.terms);
      if (!s) continue;
      score += s;
    }
    hits.push({ r, score });
  }
  return hits;
}

export function searchArticles(data: PreparedArticle[], q: ParsedQuery, lawFilter?: string) {
  const hits: { a: PreparedArticle; score: number }[] = [];
  const law = lawFilter || q.lawHint;
  for (const a of data) {
    if (law && a.law.id !== law) continue;
    if (q.article && a.key !== q.article) continue;
    if (q.docno || q.date) continue;
    let score = 1 + (a.law.core ? 2 : 0);
    if (q.terms.length) {
      const s = scoreFields([[a.n, 3], [a.t, 1]], q.terms);
      if (!s) continue;
      score += s;
    } else if (!law && !q.article) continue;
    hits.push({ a, score });
  }
  return hits;
}

export function searchTech(data: PreparedTech[], q: ParsedQuery, f: { agency?: string; topic?: string } = {}) {
  const hits: { r: TechIdx; score: number }[] = [];
  if (q.docno || q.article || q.lawHint) return hits;
  for (const p of data) {
    if (q.date && (!p.r.d || !q.date.startsWith(p.r.d))) continue;
    if (f.agency && p.r.ag !== f.agency) continue;
    if (f.topic && !p.r.tp.includes(f.topic)) continue;
    let score = 1;
    if (q.terms.length) {
      const s = scoreFields([[p.t, 4], [p.x, 1]], q.terms);
      if (!s) continue;
      score += s;
    }
    hits.push({ r: p.r, score });
  }
  return hits;
}

/** highlight helper: returns [text, isMatch][] for display (operates on display text). */
export function highlight(text: string, terms: string[][], max = 220): [string, boolean][] {
  const variants = terms.flat().filter((v) => v.length > 0).sort((a, b) => b.length - a.length);
  const flat = text.replace(/\s+/g, " ");
  let start = 0;
  if (variants.length) {
    const lower = flat.toLowerCase();
    let pos = -1;
    for (const v of variants) { const i = lower.indexOf(v); if (i >= 0 && (pos < 0 || i < pos)) pos = i; }
    if (pos > 60) start = pos - 60;
  }
  let snippet = flat.slice(start, start + max);
  if (start > 0) snippet = "…" + snippet;
  if (start + max < flat.length) snippet += "…";
  if (!variants.length) return [[snippet, false]];
  const re = new RegExp("(" + variants.map((v) => v.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")", "gi");
  return snippet.split(re).filter(Boolean).map((part) => [part, variants.includes(part.toLowerCase())]);
}
