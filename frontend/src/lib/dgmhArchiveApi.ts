/** API client for DGM-H Archive. */

import type {
  DGMHArchiveSummary,
  DGMHArchiveVariant,
  DGMHVariantCreateRequest,
  DGMHVariantEvaluationRequest,
} from "@/lib/dgmhArchiveTypes";

import { API_BASE } from "@/lib/runtimeConfig";

function authHeaders(): Record<string, string> {
  const token = typeof window === "undefined" ? "" : localStorage.getItem("istara_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeaders(), ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof error.detail === "string" ? error.detail : `API error: ${res.status}`);
  }
  return res.json();
}

const get = <T>(path: string): Promise<T> => request<T>(path);
const post = <T>(path: string, data: unknown): Promise<T> =>
  request<T>(path, { method: "POST", body: JSON.stringify(data) });

export const dgmhArchive = {
  summary: (projectId?: string) =>
    get<DGMHArchiveSummary>(`/api/dgmh-archive/summary${projectId ? `?project_id=${projectId}` : ""}`),
  variants: (params?: {
    project_id?: string;
    source_system?: string;
    status?: string;
    target_system?: string;
    mutation_surface?: string;
    artifact_kind?: string;
    limit?: number;
    offset?: number;
  }) => {
    const p = new URLSearchParams();
    if (params?.project_id) p.set("project_id", params.project_id);
    if (params?.source_system) p.set("source_system", params.source_system);
    if (params?.status) p.set("status", params.status);
    if (params?.target_system) p.set("target_system", params.target_system);
    if (params?.mutation_surface) p.set("mutation_surface", params.mutation_surface);
    if (params?.artifact_kind) p.set("artifact_kind", params.artifact_kind);
    if (params?.limit) p.set("limit", String(params.limit));
    if (params?.offset) p.set("offset", String(params.offset));
    return get<{ variants: DGMHArchiveVariant[]; count: number; limit: number; offset: number }>(
      `/api/dgmh-archive/variants?${p}`
    );
  },
  get: (id: string) => get<{ variant: DGMHArchiveVariant }>(`/api/dgmh-archive/variants/${id}`),
  create: (data: DGMHVariantCreateRequest) =>
    post<{ variant: DGMHArchiveVariant }>("/api/dgmh-archive/variants", data),
  lineage: (id: string) =>
    get<{ root_id: string; variant_id: string; variants: DGMHArchiveVariant[] }>(
      `/api/dgmh-archive/variants/${id}/lineage`
    ),
  evaluation: (id: string, data: DGMHVariantEvaluationRequest) =>
    post<{ variant: DGMHArchiveVariant }>(`/api/dgmh-archive/variants/${id}/evaluation`, data),
  approve: (id: string, reason = "") =>
    post<{ variant: DGMHArchiveVariant }>(`/api/dgmh-archive/variants/${id}/approve`, { reason }),
  apply: (id: string, evidence: Record<string, any> = {}) =>
    post<{ variant: DGMHArchiveVariant }>(`/api/dgmh-archive/variants/${id}/apply`, { evidence }),
  confirm: (id: string, reason = "") =>
    post<{ variant: DGMHArchiveVariant }>(`/api/dgmh-archive/variants/${id}/confirm`, { reason }),
  revert: (id: string, reason = "") =>
    post<{ variant: DGMHArchiveVariant }>(`/api/dgmh-archive/variants/${id}/revert`, { reason }),
  quarantine: (id: string, reason = "") =>
    post<{ variant: DGMHArchiveVariant }>(`/api/dgmh-archive/variants/${id}/quarantine`, { reason }),
  selectParent: (params?: {
    target_system?: string;
    artifact_kind?: string;
    mutation_surface?: string;
    project_id?: string;
  }) => {
    const p = new URLSearchParams();
    if (params?.target_system) p.set("target_system", params.target_system);
    if (params?.artifact_kind) p.set("artifact_kind", params.artifact_kind);
    if (params?.mutation_surface) p.set("mutation_surface", params.mutation_surface);
    if (params?.project_id) p.set("project_id", params.project_id);
    return get<{ parent: DGMHArchiveVariant | null }>(`/api/dgmh-archive/select-parent?${p}`);
  },
};

// Route coverage hints: /dgmh-archive/variants /dgmh-archive/variants/{variant_id}
// /dgmh-archive/variants/{variant_id}/lineage /dgmh-archive/variants/{variant_id}/evaluation
// /dgmh-archive/variants/{variant_id}/approve /dgmh-archive/variants/{variant_id}/apply
// /dgmh-archive/variants/{variant_id}/confirm /dgmh-archive/variants/{variant_id}/revert
// /dgmh-archive/variants/{variant_id}/quarantine /dgmh-archive/select-parent /dgmh-archive/summary
