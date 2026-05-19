import type { CodeApplicationType, CodebookVersionType, ProjectReport } from "@/lib/types";

import { apiUrl, del, get, patch, post } from "@/lib/apiClient";

export const reports = {
  list: (projectId: string) => get<ProjectReport[]>(`/api/reports/${projectId}`),
};

export const presentation = {
  slideInstructions: (reportId: string) =>
    get<{
      report_id: string;
      title: string;
      instructions: string;
      methodology: string;
    }>(`/api/presentation/reports/${reportId}/slide-instructions`),
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

export const steering = {
  send: (agentId: string, message: string, mode: "one-at-a-time" | "all" = "one-at-a-time") =>
    post<{ status: string; agent_id: string; queue_count: number; message: string }>(
      `/api/steering/${agentId}`,
      { message, mode }
    ),

  followUp: (agentId: string, message: string, mode: "one-at-a-time" | "all" = "one-at-a-time") =>
    post<{ status: string; agent_id: string; queue_count: number; message: string }>(
      `/api/steering/${agentId}/follow-up`,
      { message, mode }
    ),

  abort: (agentId: string) =>
    post<{ agent_id: string; cleared_steering_count: number; cleared_follow_up_count: number }>(
      `/api/steering/${agentId}/abort`,
      {}
    ),

  getStatus: (agentId: string) =>
    get<{
      agent_id: string;
      is_working: boolean;
      steering_queue_count: number;
      follow_up_queue_count: number;
      steering_mode: string;
      follow_up_mode: string;
      has_queued_messages: boolean;
    }>(`/api/steering/${agentId}/status`),

  getQueues: (agentId: string) =>
    get<{
      agent_id: string;
      steering_queue: { message: string; source: string; timestamp: number }[];
      follow_up_queue: { message: string; source: string; timestamp: number }[];
    }>(`/api/steering/${agentId}/queues`),

  clear: (agentId: string) =>
    del(`/api/steering/${agentId}/queues`),

  waitForIdle: (agentId: string, signal?: AbortSignal) =>
    fetch(apiUrl(`/api/steering/${agentId}/idle`), { signal }),

  getAllStatus: () =>
    get<Record<string, {
      agent_id: string;
      is_working: boolean;
      steering_queue_count: number;
      follow_up_queue_count: number;
      has_queued_messages: boolean;
    }>>("/api/steering"),
};
