import type { InterpDetail, InterpIdx, LawDetail, LawIdx, LawVersion, Manifest, RunLog, TechIdx } from "./types";

const cache = new Map<string, Promise<unknown>>();
export const base = "./data/";

export function load<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    const p = fetch(base + path, { cache: "no-cache" }).then((r) => {
      if (!r.ok) throw new Error(`無法載入資料（${r.status}）：${path}`);
      return r.json();
    });
    p.catch(() => cache.delete(path));
    cache.set(path, p);
  }
  return cache.get(path) as Promise<T>;
}

export const getManifest = () => load<Manifest>("manifest.json");
export const getLaws = () => load<LawIdx[]>("search-laws.json");
export const getInterps = () => load<InterpIdx[]>("search-interps.json");
export const getTech = () => load<TechIdx[]>("search-tech.json");
export const getLaw = (id: string) => load<LawDetail>(`laws/${encodeURIComponent(id)}.json`);
export const getInterp = (id: string) => load<InterpDetail>(`interps/${encodeURIComponent(id)}.json`);
export const getVersion = (law: string, v: string) => load<LawVersion>(`versions/${encodeURIComponent(law)}/${encodeURIComponent(v)}.json`);
export const getUpdates = () => load<RunLog[]>("updates.json");
export const getSources = () => load<SourcesData>("sources.json");

export interface SourcesData {
  registry: { last_reviewed: string; sources: Record<string, unknown>[] };
  status: Record<string, { last_checked?: string; last_status?: string; last_success?: string; last_full_compare?: string; last_changed?: string; last_errors?: string[] }>;
  audit: Record<string, { reachable: boolean | null; robots_allowed?: boolean; http_status?: number; error?: string; checked_at: string }>;
  audit_checked_at?: string;
  agencies: { id: string; name: string; short?: string; level: string; priority: number; official_site: string | null; relevance?: string; note?: string }[];
  historical: { reorg_date: string; mappings: { historical: string; aliases?: string[]; successor: string; note?: string }[] };
  per_agency: Record<string, { laws: number; interps: number; tech: number }>;
  catalog: { discovered_at: string; datasets: { unit_id: string; title: string; organ: string; agency_id: string }[] } | null;
  local_candidates?: Record<string, { checked_at: string; candidates: { law_system_id: string; name: string; url: string }[] }> | null;
}
