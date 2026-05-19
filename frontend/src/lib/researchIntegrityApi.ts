import type { CodeApplicationType, CodebookVersionType, ProjectReport } from "@/lib/types";

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
  list: (projectId: string, status?: string) =>
    get<CodeApplicationType[]>(`/api/code-applications/${projectId}${status ? `?status=${status}` : ""}`),
  pending: (projectId: string) =>
    get<CodeApplicationType[]>(`/api/code-applications/${projectId}/pending`),
  review: (applicationId: string, reviewStatus: string, projectId: string, reviewedBy?: string) =>
    patch<CodeApplicationType>(`/api/code-applications/${applicationId}/review?project_id=${encodeURIComponent(projectId)}`, {
      review_status: reviewStatus,
      reviewed_by: reviewedBy || "user",
    }),
  bulkApprove: (projectId: string, minConfidence?: number) =>
    post<{ approved_count: number }>(
      `/api/code-applications/${projectId}/bulk-approve?min_confidence=${minConfidence || 0.9}`,
      {}
    ),
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
