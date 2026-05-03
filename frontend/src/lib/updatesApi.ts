import { API_BASE } from "@/lib/runtimeConfig";

type UpdateConfirmation = {
  confirm: "PREPARE_UPDATE" | "APPLY_UPDATE";
};

export type UpdateVersion = {
  version: string;
  format: string;
  description: string;
};

export type UpdateInfo = {
  update_available: boolean;
  current_version: string;
  latest_version: string;
  release_name?: string;
  published_at?: string;
  changelog?: string;
  release_url?: string;
  downloads?: Record<string, string>;
  method?: string;
  source_checkout_includes_latest_release?: boolean;
  message?: string;
  error?: string;
};

type UpdatePrepareResult = {
  status: "ready";
  backup_id: string;
  message: string;
  current_version: string;
};

type UpdateApplyResult = {
  status: "updating";
  message: string;
  install_dir: string;
};

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("istara_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...getAuthHeaders(), ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof error.detail === "string" ? error.detail : "Update request failed");
  }
  return response.json();
}

function post<T>(path: string, body: UpdateConfirmation): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export const updatesApi = {
  version: () => request<UpdateVersion>("/api/updates/version"),
  check: () => request<UpdateInfo>("/api/updates/check"),
  prepare: () => post<UpdatePrepareResult>("/api/updates/prepare", { confirm: "PREPARE_UPDATE" }),
  apply: () => post<UpdateApplyResult>("/api/updates/apply", { confirm: "APPLY_UPDATE" }),
};
