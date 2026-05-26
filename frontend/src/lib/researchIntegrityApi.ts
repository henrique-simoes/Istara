import type {
  CodeApplicationType,
  CodebookVersionType,
  EvidenceGraphTraceabilityType,
  ProjectReport,
  ReconciliationDecisionType,
  ResearchValidityTelemetryAuditType,
  StartCodingRunRequest,
} from "@/lib/types";

import { apiUrl, del, get, patch, post } from "@/lib/apiClient";

export const reports = {
  list: (projectId: string) => get<ProjectReport[]>(`/api/reports/${projectId}`),
};

export const presentation = {
  slideInstructions: (reportId: string, projectId: string) =>
    get<{
      report_id: string;
      project_id: string;
      title: string;
      instructions: string;
      methodology: string;
    }>(`/api/presentation/reports/${reportId}/slide-instructions?project_id=${encodeURIComponent(projectId)}`),
};

export const codebookVersions = {
  list: (projectId: string) => get<CodebookVersionType[]>(`/api/codebook-versions/${projectId}`),
  latest: (projectId: string) => get<CodebookVersionType>(`/api/codebook-versions/${projectId}/latest`),
  create: (data: {
    project_id: string;
    version: string;
    codes: unknown[];
    change_log: string;
    methodology?: string;
  }) => post<CodebookVersionType>("/api/codebook-versions", data),
};

export const codebooks = {
  list: (projectId: string) => get<any[]>(`/api/codebooks?project_id=${projectId}`),
};

export const codeApplications = {
  list: (projectId: string, status?: string, taskId?: string) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (taskId) params.set("task_id", taskId);
    const query = params.toString();
    return get<CodeApplicationType[]>(`/api/code-applications/${projectId}${query ? `?${query}` : ""}`);
  },
  pending: (projectId: string) =>
    get<CodeApplicationType[]>(`/api/code-applications/${projectId}/pending`),
  review: (
    applicationId: string,
    reviewStatus: string,
    projectId: string,
    reviewedBy?: string,
    rationale?: string,
    acceptedCodeId?: string
  ) =>
    patch<CodeApplicationType>(`/api/code-applications/${applicationId}/review?project_id=${encodeURIComponent(projectId)}`, {
      review_status: reviewStatus,
      reviewed_by: reviewedBy || "user",
      rationale: rationale || "",
      accepted_code_id: acceptedCodeId || null,
    }),
  bulkApprove: (projectId: string, minConfidence?: number) =>
    post<{ approved_count: number }>(
      `/api/code-applications/${projectId}/bulk-approve?min_confidence=${minConfidence || 0.9}`,
      {}
    ),
};

export const researchValidity = {
  contract: () =>
    get<{
      contract: Record<string, unknown>;
      qualitative_coding_protocol: Record<string, unknown>;
      telemetry_operations: string[];
      telemetry_contract: Record<string, unknown>;
    }>("/api/research-validity/contract"),
  summary: (projectId: string) =>
    get<{
      project_id: string;
      evidence_unit_count: number;
      coding_run_count: number;
      pending_review_count: number;
      accepted_code_application_count: number;
      low_consensus_or_blocked_count: number;
      reconciliation_decision_count: number;
      report_gate: string;
    }>(`/api/research-validity/${projectId}/summary`),
  evidenceUnits: (projectId: string, limit = 100, taskId?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (taskId) params.set("task_id", taskId);
    return get<Record<string, unknown>[]>(
      `/api/research-validity/${projectId}/evidence-units?${params.toString()}`
    );
  },
  codingRuns: (projectId: string, limit = 50, taskId?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (taskId) params.set("task_id", taskId);
    return get<Record<string, unknown>[]>(
      `/api/research-validity/${projectId}/coding-runs?${params.toString()}`
    );
  },
  startCodingRun: (
    projectId: string,
    payload: StartCodingRunRequest = {}
  ) => post<Record<string, unknown>>(`/api/research-validity/${projectId}/coding-runs`, payload),
  evidenceGraph: (projectId: string, limit = 200) =>
    get<Record<string, unknown>[]>(
      `/api/research-validity/${projectId}/evidence-graph?limit=${limit}`
    ),
  telemetryAudit: (projectId: string, limit = 500) =>
    get<ResearchValidityTelemetryAuditType>(
      `/api/research-validity/${projectId}/telemetry-audit?limit=${limit}`
    ),
  traceability: (
    projectId: string,
    options: { reportId?: string; taskId?: string; findingId?: string; limit?: number } = {}
  ) => {
    const params = new URLSearchParams({ limit: String(options.limit || 50) });
    if (options.reportId) params.set("report_id", options.reportId);
    if (options.taskId) params.set("task_id", options.taskId);
    if (options.findingId) params.set("finding_id", options.findingId);
    return get<EvidenceGraphTraceabilityType>(
      `/api/research-validity/${projectId}/traceability?${params.toString()}`
    );
  },
  reconciliationDecisions: (
    projectId: string,
    options: { taskId?: string; codingRunId?: string; evidenceUnitId?: string; limit?: number } = {}
  ) => {
    const params = new URLSearchParams({ limit: String(options.limit || 100) });
    if (options.taskId) params.set("task_id", options.taskId);
    if (options.codingRunId) params.set("coding_run_id", options.codingRunId);
    if (options.evidenceUnitId) params.set("evidence_unit_id", options.evidenceUnitId);
    return get<ReconciliationDecisionType[]>(
      `/api/research-validity/${projectId}/reconciliation-decisions?${params.toString()}`
    );
  },
};

const steeringProjectParam = (projectId: string) => `project_id=${encodeURIComponent(projectId)}`;

export const steering = {
  send: (
    agentId: string,
    message: string,
    projectId: string,
    mode: "one-at-a-time" | "all" = "one-at-a-time"
  ) =>
    post<{ status: string; agent_id: string; queue_count: number; message: string }>(
      `/api/steering/${agentId}`,
      { message, mode, project_id: projectId }
    ),

  followUp: (
    agentId: string,
    message: string,
    projectId: string,
    mode: "one-at-a-time" | "all" = "one-at-a-time"
  ) =>
    post<{ status: string; agent_id: string; queue_count: number; message: string }>(
      `/api/steering/${agentId}/follow-up`,
      { message, mode, project_id: projectId }
    ),

  abort: (agentId: string, projectId: string) =>
    post<{ agent_id: string; cleared_steering_count: number; cleared_follow_up_count: number }>(
      `/api/steering/${agentId}/abort?${steeringProjectParam(projectId)}`,
      {}
    ),

  getStatus: (agentId: string, projectId: string) =>
    get<{
      agent_id: string;
      project_id: string;
      is_working: boolean;
      steering_queue_count: number;
      follow_up_queue_count: number;
      steering_mode: string;
      follow_up_mode: string;
      has_queued_messages: boolean;
    }>(`/api/steering/${agentId}/status?${steeringProjectParam(projectId)}`),

  getQueues: (agentId: string, projectId: string) =>
    get<{
      agent_id: string;
      project_id: string;
      steering_queue: { message: string; source: string; timestamp: number; metadata?: Record<string, unknown> }[];
      follow_up_queue: { message: string; source: string; timestamp: number; metadata?: Record<string, unknown> }[];
    }>(`/api/steering/${agentId}/queues?${steeringProjectParam(projectId)}`),

  clear: (agentId: string, projectId: string) =>
    del(`/api/steering/${agentId}/queues?${steeringProjectParam(projectId)}`),

  waitForIdle: (agentId: string, projectId: string, signal?: AbortSignal) =>
    fetch(apiUrl(`/api/steering/${agentId}/idle?${steeringProjectParam(projectId)}`), { signal }),

  getAllStatus: (projectId: string) =>
    get<Record<string, {
      agent_id: string;
      project_id: string;
      is_working: boolean;
      steering_queue_count: number;
      follow_up_queue_count: number;
      has_queued_messages: boolean;
    }>>(`/api/steering?${steeringProjectParam(projectId)}`),
};
