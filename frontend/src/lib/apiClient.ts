import { API_BASE } from "@/lib/runtimeConfig";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export function authHeaders(): Record<string, string> {
  const token = typeof window === "undefined" ? "" : localStorage.getItem("istara_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json", ...authHeaders(), ...options?.headers },
    ...options,
  });
  if (res.status === 401) {
    const hadToken = !!localStorage.getItem("istara_token");
    localStorage.removeItem("istara_token");
    if (hadToken && typeof window !== "undefined") {
      window.dispatchEvent(new Event("istara:auth-changed"));
      window.dispatchEvent(new Event("istara:auth-expired"));
    }
    throw new Error("Authentication required");
  }
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = error.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join("; ")
          : typeof detail === "object" && detail !== null
            ? JSON.stringify(detail)
            : `API error: ${res.status}`;
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function post<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(data) });
}

export function patch<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, { method: "PATCH", body: JSON.stringify(data) });
}

export function del(path: string): Promise<void> {
  return request<void>(path, { method: "DELETE" });
}
