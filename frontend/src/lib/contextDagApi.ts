import type { DAGExpandResult, DAGGrepResult, DAGHealth, DAGNode } from "@/lib/types";
import { API_BASE } from "@/lib/runtimeConfig";

function authHeaders(): Record<string, string> {
  const token = typeof window === "undefined" ? "" : localStorage.getItem("istara_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function json<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeaders(), ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(((await res.json().catch(() => ({}))) as any).detail || `API error: ${res.status}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

function scopedDagPath(sessionId: string, projectId: string, suffix = ""): string {
  const params = new URLSearchParams({ project_id: projectId });
  return `/api/context-dag/${encodeURIComponent(sessionId)}${suffix}?${params.toString()}`;
}

export const contextDag = {
  getStructure: (sessionId: string, projectId: string) =>
    json<{
      session_id: string;
      nodes: DAGNode[];
      stats: DAGHealth;
    }>(scopedDagPath(sessionId, projectId)),
  health: (sessionId: string, projectId: string) =>
    json<DAGHealth>(scopedDagPath(sessionId, projectId, "/health")),
  expand: (sessionId: string, projectId: string, nodeId: string) =>
    json<DAGExpandResult>(scopedDagPath(sessionId, projectId, "/expand"), {
      method: "POST",
      body: JSON.stringify({ node_id: nodeId }),
    }),
  grep: (sessionId: string, projectId: string, query: string) =>
    json<DAGGrepResult>(scopedDagPath(sessionId, projectId, "/grep"), {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  node: (sessionId: string, projectId: string, nodeId: string) =>
    json<DAGNode>(scopedDagPath(sessionId, projectId, `/node/${encodeURIComponent(nodeId)}`)),
  compact: (sessionId: string, projectId: string) =>
    json<{ compacted: boolean }>(scopedDagPath(sessionId, projectId, "/compact"), {
      method: "POST",
      body: "{}",
    }),
};
