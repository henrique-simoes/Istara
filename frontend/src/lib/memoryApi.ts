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

export const memory = {
  list: (projectId: string, page = 1, pageSize = 50) =>
    json<{
      chunks: Array<{
        text: string;
        source: string;
        page: number;
        agent_id: string;
        chunk_type: string;
        created_at: number;
        confidence: number;
      }>;
      total: number;
      page: number;
      page_size: number;
      sources?: Array<{ name: string; count: number }>;
      error?: string;
    }>(`/api/memory/${projectId}?page=${page}&page_size=${pageSize}`),
  search: (
    projectId: string,
    query: string,
    topK = 20,
    filters?: { source?: string; file_type?: string }
  ) => {
    const params = new URLSearchParams({ query, top_k: String(topK) });
    if (filters?.source) params.set("source", filters.source);
    if (filters?.file_type) params.set("file_type", filters.file_type);
    return json<{
      results: Array<{
        text: string;
        source: string;
        score: number;
        page: number | null;
      }>;
      query: string;
      total: number;
      filters?: { source: string | null; file_type: string | null };
    }>(`/api/memory/${projectId}/search?${params.toString()}`);
  },
  stats: (projectId: string) =>
    json<{
      vector_chunks: number;
      keyword_chunks: number;
      sources: Array<{ name: string; chunk_count: number }>;
      embedding_model: string;
      vector_dimensions: number;
      chunk_size: number;
      chunk_overlap: number;
      hybrid_weights: { vector: number; keyword: number };
    }>(`/api/memory/${projectId}/stats`),
  agentNotes: (projectId: string, agentId: string) =>
    json<{
      agent_id: string;
      project_id: string;
      notes: Array<{ text: string; source: string }>;
    }>(`/api/memory/${projectId}/agent/${agentId}/notes`),
  deleteSource: (projectId: string, sourceName: string) =>
    json<{ deleted: boolean; source: string }>(
      `/api/memory/${projectId}/source/${encodeURIComponent(sourceName)}`,
      { method: "DELETE" }
    ),
};
