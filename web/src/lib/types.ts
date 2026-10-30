export type Article = [key: string, label: string | null, chapter: string | null, text: string];
export interface LawIdx { id: string; n: string; lv: string; st: string; md: string | null; tp: string[]; core: boolean; src: string; a: Article[]; h?: [string, string][] }
export interface InterpIdx {
  id: string; no: string; d: string | null; ag: string; agid: string | null; h: boolean; cat: string; s: string; c: string;
  tp: string[]; v: string; rel: [lawId: string, article: string | null, kind: string][]; fl: string[];
}
export interface TechIdx {
  id: string; t: string; se: string; is: string; ag: string; au: string; d: string | null; u: string | null; tp: string[];
  isbn?: string | null; gpn?: string | null; pg?: string | null; ds?: string; dsu?: string; lic?: string; ls?: string;
}
export interface Manifest {
  built_at: string; git_sha: string;
  counts: { laws: number; articles: number; interps: number; tech: number; law_versions: number };
  validity_counts: Record<string, number>; validity_labels: Record<string, string>;
  last_success: Record<string, string | null>; last_success_any: string | null;
  latest_run: { run_id: string; mode: string; started_at: string; finished_at: string; result: string } | null;
  law_names: Record<string, string>; agency_names: Record<string, string>;
  topics: { legal_topics: Record<string, { label: string; keywords: string[] }>; technical_topics: Record<string, { group: string; label: string; keywords: string[] }> };
  synonyms: string[][];
  latest: { interps: string[]; tech: string[]; laws: string[] };
}
export interface Relation { law_id: string; article: string | null; kind: "official" | "extracted" | "manual"; evidence?: string; snippet?: string; note?: string }
export interface InterpDetail {
  id: string; docno: string; date: string | null; date_text: string; agency_text: string; agency_id: string | null; agency_name: string | null;
  historical_name: string | null; is_historical: boolean; category: string; subject: string; content: string; memo: string;
  sources: { source_id: string; url: string; fetched_at: string; source_key: string }[];
  validity: { status: string; confirmed: boolean; basis: Record<string, unknown>[]; notes?: string[] };
  topics: string[]; flags: string[]; relations: Relation[]; first_seen: string; last_synced: string; version: number;
  history?: { at: string; changed_fields: string[]; previous: Record<string, string> }[]; source_missing_since?: string;
}
export interface LawVersionRef { id: string; date: string | null; kind: "captured" | "official_history"; full: boolean; entry: string | null; url: string | null }
export interface LawDetail {
  id: string; name: string; level: string; category: string; official_url: string; modified_date: string | null; effective_date: string | null;
  effective_note: string; abandon_note: string; status: string; histories: { seq: number; text: string; date: string | null }[];
  articles: { key: string; label: string; chapter: string | null; text: string }[]; attachments: { name: string; url: string | null }[];
  topics: string[]; core: boolean; sources: { source_id: string; url: string; fetched_at: string; dataset_update?: string }[];
  primary_source: string; rmis?: { url: string; lawexp_url: string | null; modified_date: string | null; histories: { text: string; date: string | null; rmis_history_id: number | null }[] };
  cross_check?: { rmis_modified: string | null; moj_modified: string | null; text_differs: string[]; at: string };
  flags?: string[]; former_names?: string[]; last_checked: string; last_changed: string; first_seen: string;
  change_log?: { at: string; from_modified: string | null; to_modified: string | null; articles: string[] }[];
  versions: LawVersionRef[]; foreword?: string;
}
export interface LawVersion { law_id: string; version_id: string; name: string; modified_date: string | null; kind: string; is_full_text: boolean;
  articles: { key: string; label: string; chapter: string | null; text: string }[]; content?: string; entry?: string; url?: string; note?: string; captured_at: string }
export interface RunLog {
  run_id: string; mode: string; started_at: string; finished_at: string; result: string; deploy?: string;
  sources: { source_id: string; status: string; complete: boolean; added: number; modified: number; status_changed: number; unchanged: number;
    rejected: number; failed: number; missing_flagged: number; requests: number; notes: string[]; errors: string[] }[];
  events: { kind: string; [k: string]: unknown }[];
  postprocess?: Record<string, unknown>;
}
