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

export const contextDag = {
  getStructure: (sessionId: string) =>
    json<{
      session_id: string;
      nodes: DAGNode[];
      stats: DAGHealth;
    }>(`/api/context-dag/${sessionId}`),
  health: (sessionId: string) =>
    json<DAGHealth>(`/api/context-dag/${sessionId}/health`),
  expand: (sessionId: string, nodeId: string) =>
    json<DAGExpandResult>(`/api/context-dag/${sessionId}/expand`, {
      method: "POST",
      body: JSON.stringify({ node_id: nodeId }),
    }),
  grep: (sessionId: string, query: string) =>
    json<DAGGrepResult>(`/api/context-dag/${sessionId}/grep`, {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  node: (sessionId: string, nodeId: string) =>
    json<DAGNode>(`/api/context-dag/${sessionId}/node/${nodeId}`),
  compact: (sessionId: string) =>
    json<{ compacted: boolean }>(`/api/context-dag/${sessionId}/compact`, {
      method: "POST",
      body: "{}",
    }),
};
