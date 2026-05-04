/** API client for Improvement Governance. */

import type {
  ImprovementFeatureContract,
  ImprovementGovernanceSummary,
  ImprovementProposal,
  ImprovementProposalCreateRequest,
  ProposalEvaluationRequest,
} from "@/lib/improvementGovernanceTypes";

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

export const improvementGovernance = {
  summary: (projectId?: string) =>
    get<ImprovementGovernanceSummary>(
      `/api/improvement-governance/summary${projectId ? `?project_id=${projectId}` : ""}`
    ),
  proposals: (params?: {
    project_id?: string;
    source_system?: string;
    status?: string;
    affected_surface?: string;
    limit?: number;
    offset?: number;
  }) => {
    const p = new URLSearchParams();
    if (params?.project_id) p.set("project_id", params.project_id);
    if (params?.source_system) p.set("source_system", params.source_system);
    if (params?.status) p.set("status", params.status);
    if (params?.affected_surface) p.set("affected_surface", params.affected_surface);
    if (params?.limit) p.set("limit", String(params.limit));
    if (params?.offset) p.set("offset", String(params.offset));
    return get<{ proposals: ImprovementProposal[]; count: number; limit: number; offset: number }>(
      `/api/improvement-governance/proposals?${p}`
    );
  },
  get: (id: string) => get<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}`),
  create: (data: ImprovementProposalCreateRequest) =>
    post<{ proposal: ImprovementProposal }>("/api/improvement-governance/proposals", data),
  approve: (id: string, note = "") =>
    post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/approve`, { note }),
  apply: (id: string, evidence: Record<string, any> = {}) =>
    post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/apply`, { evidence }),
  reject: (id: string, reason = "") =>
    post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/reject`, { reason }),
  revert: (id: string, reason = "") =>
    post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/revert`, { reason }),
  quarantine: (id: string, reason = "") =>
    post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/quarantine`, { reason }),
  evaluation: (
    id: string,
    data: ProposalEvaluationRequest
  ) => post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/evaluation`, data),
  featureContract: () =>
    get<{ features: ImprovementFeatureContract[] }>("/api/improvement-governance/feature-contract"),
};

// Route coverage hints: /improvement-governance/proposals /improvement-governance/proposals/{proposal_id} /improvement-governance/proposals/{proposal_id}/approve /improvement-governance/proposals/{proposal_id}/apply /improvement-governance/proposals/{proposal_id}/reject /improvement-governance/proposals/{proposal_id}/revert /improvement-governance/proposals/{proposal_id}/quarantine /improvement-governance/proposals/{proposal_id}/evaluation /improvement-governance/summary /improvement-governance/feature-contract
