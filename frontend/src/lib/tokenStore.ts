/**
 * Token custody: the session bearer token lives in memory only.
 *
 * Rationale: `localStorage` is readable by any script running on the page,
 * so a stored bearer token turns any XSS into a 24h credential theft
 * (audit F4). The server sets an HttpOnly `__Host-` session cookie on login
 * and every API call sends `credentials: "include"`, so the cookie is the
 * primary transport; the in-memory token covers WebSocket setup and any
 * surface the cookie cannot reach.
 *
 * `localStorage("istara_token")` remains a READ-ONLY legacy fallback so
 * sessions minted before this change (and automation that injects one) keep
 * working until logout. Nothing in the product writes it anymore.
 */

const LEGACY_KEY = "istara_token";

let memoryToken: string | null = null;

export function getToken(): string | null {
  if (memoryToken) return memoryToken;
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(LEGACY_KEY);
  } catch {
    return null;
  }
}

/** Store a freshly minted token in memory. Never writes localStorage. */
export function setToken(token: string | null): void {
  memoryToken = token || null;
}

export function clearToken(): void {
  memoryToken = null;
  if (typeof window !== "undefined") {
    try {
      localStorage.removeItem(LEGACY_KEY);
    } catch {
      /* storage unavailable — memory already cleared */
    }
  }
}

/** True when any credential (memory or legacy) is available. */
export function hasToken(): boolean {
  return getToken() !== null;
}
