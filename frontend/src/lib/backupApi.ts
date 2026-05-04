import type { BackupConfig, BackupRecord } from "@/lib/types";
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

export const backups = {
  list: () => json<{ backups: BackupRecord[]; total: number }>("/api/backups"),
  create: (type: "full" | "incremental" = "full") => json<BackupRecord>("/api/backups/create", { method: "POST", body: JSON.stringify({ backup_type: type }) }),
  restore: (id: string) => json<any>(`/api/backups/${id}/restore`, { method: "POST" }),
  verify: (id: string) => json<any>(`/api/backups/${id}/verify`, { method: "POST" }),
  remove: (id: string) => json<void>(`/api/backups/${id}`, { method: "DELETE" }),
  download: async (id: string) => {
    const res = await fetch(`${API_BASE}/api/backups/${id}/download`, { headers: { ...authHeaders() } });
    if (!res.ok) throw new Error(((await res.json().catch(() => ({}))) as any).detail || `Download failed: ${res.status}`);
    return res.blob();
  },
  config: () => json<BackupConfig>("/api/backups/config"),
  updateConfig: (data: Partial<BackupConfig>) => json<any>("/api/backups/config", { method: "POST", body: JSON.stringify(data) }),
  estimate: () => json<any>("/api/backups/estimate"),
  uploadRestore: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${API_BASE}/api/backups/upload-restore`, { method: "POST", headers: authHeaders(), body: formData }).then(async (r) => {
      if (!r.ok) throw new Error(((await r.json().catch(() => ({}))) as any).detail || `Upload failed: ${r.status}`);
      return r.json();
    });
  },
};
