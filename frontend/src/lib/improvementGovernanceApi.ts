/** API client for Improvement Governance. */

import type {
  ImprovementFeatureContract,
  ImprovementGovernanceSummary,
  ImprovementProposal,
  ImprovementProposalCreateRequest,
  ProposalSandboxEvaluation,
  ProposalSandboxEvaluationRequest,
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

function projectQuery(projectId: string): string {
  return `project_id=${encodeURIComponent(projectId)}`;
}

export const improvementGovernance = {
  summary: (projectId: string) =>
    get<ImprovementGovernanceSummary>(`/api/improvement-governance/summary?${projectQuery(projectId)}`),
  proposals: (params: {
    project_id: string;
    source_system?: string;
    status?: string;
    affected_surface?: string;
    limit?: number;
    offset?: number;
  }) => {
    const p = new URLSearchParams();
    p.set("project_id", params.project_id);
    if (params.source_system) p.set("source_system", params.source_system);
    if (params.status) p.set("status", params.status);
    if (params.affected_surface) p.set("affected_surface", params.affected_surface);
    if (params.limit) p.set("limit", String(params.limit));
    if (params.offset) p.set("offset", String(params.offset));
    return get<{ proposals: ImprovementProposal[]; count: number; limit: number; offset: number }>(
      `/api/improvement-governance/proposals?${p}`
    );
  },
  get: (id: string, projectId: string) =>
    get<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}?${projectQuery(projectId)}`),
  create: (data: ImprovementProposalCreateRequest) =>
    post<{ proposal: ImprovementProposal }>("/api/improvement-governance/proposals", data),
  approve: (id: string, projectId: string, note = "") =>
    post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/approve?${projectQuery(projectId)}`, { note }),
  apply: (id: string, projectId: string, evidence: Record<string, any> = {}) =>
    post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/apply?${projectQuery(projectId)}`, { evidence }),
  reject: (id: string, projectId: string, reason = "") =>
    post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/reject?${projectQuery(projectId)}`, { reason }),
  revert: (id: string, projectId: string, reason = "") =>
    post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/revert?${projectQuery(projectId)}`, { reason }),
  quarantine: (id: string, projectId: string, reason = "") =>
    post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/quarantine?${projectQuery(projectId)}`, { reason }),
  evaluation: (
    id: string,
    projectId: string,
    data: ProposalEvaluationRequest
  ) => post<{ proposal: ImprovementProposal }>(`/api/improvement-governance/proposals/${id}/evaluation?${projectQuery(projectId)}`, data),
  sandboxEvaluation: (id: string, projectId: string, data: ProposalSandboxEvaluationRequest = {}) =>
    post<{ proposal: ImprovementProposal; sandbox_evaluation: ProposalSandboxEvaluation }>(
      `/api/improvement-governance/proposals/${id}/sandbox-evaluation?${projectQuery(projectId)}`,
      data
    ),
  featureContract: () =>
    get<{ features: ImprovementFeatureContract[] }>("/api/improvement-governance/feature-contract"),
};

// Route coverage hints: /improvement-governance/proposals /improvement-governance/proposals/{proposal_id} /improvement-governance/proposals/{proposal_id}/approve /improvement-governance/proposals/{proposal_id}/apply /improvement-governance/proposals/{proposal_id}/reject /improvement-governance/proposals/{proposal_id}/revert /improvement-governance/proposals/{proposal_id}/quarantine /improvement-governance/proposals/{proposal_id}/evaluation /improvement-governance/proposals/{proposal_id}/sandbox-evaluation /improvement-governance/summary /improvement-governance/feature-contract
