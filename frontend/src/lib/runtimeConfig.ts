const DEFAULT_BACKEND_PORT = "8000";

function readPublicRuntimeSetting(name: "NEXT_PUBLIC_API_URL" | "NEXT_PUBLIC_WS_URL"): string {
  if (name === "NEXT_PUBLIC_API_URL") {
    return process.env.NEXT_PUBLIC_API_URL?.trim() || "";
  }
  return process.env.NEXT_PUBLIC_WS_URL?.trim() || "";
}

function withoutTrailingSlash(value: string): string {
  return value.replace(/\/$/, "");
}

function isLoopbackHost(hostname: string): boolean {
  const normalized = hostname.trim().toLowerCase();
  return normalized === "localhost" || normalized === "::1" || /^127(?:\.\d{1,3}){3}$/.test(normalized);
}

/**
 * Keep browser-local API URLs same-site when a deployment was built with the
 * other loopback spelling (localhost vs 127.0.0.1). Fetch Metadata treats
 * those hostnames as cross-site, which correctly blocks cookie-authenticated
 * requests. Only rewrite when both sides are loopback; explicit non-loopback
 * deployments remain authoritative.
 */
function alignLoopbackUrlWithBrowser(value: string): string {
  const normalized = withoutTrailingSlash(value);
  if (typeof window === "undefined" || !window.location.hostname) return normalized;

  try {
    const configured = new URL(normalized);
    const browserHostname = window.location.hostname;
    if (!isLoopbackHost(configured.hostname) || !isLoopbackHost(browserHostname)) {
      return normalized;
    }

    configured.hostname = browserHostname;
    configured.protocol = window.location.protocol === "https:"
      ? configured.protocol === "ws:" || configured.protocol === "wss:" ? "wss:" : "https:"
      : configured.protocol === "ws:" || configured.protocol === "wss:" ? "ws:" : "http:";
    return withoutTrailingSlash(configured.toString());
  } catch {
    return normalized;
  }
}

function browserOriginWithPort(port: string): string | null {
  if (typeof window === "undefined") return null;
  const { protocol, hostname, port: currentPort } = window.location;
  if (!hostname) return null;
  // Same-origin behind a reverse proxy (Caddy): honour the port the browser
  // is actually using (e.g. 13080 in the VPS testing deployment) instead of
  // assuming a fixed backend port. Falls back to the provided port when the
  // browser URL has no explicit port.
  const effectivePort = currentPort || port;
  return `${protocol}//${hostname}${effectivePort ? `:${effectivePort}` : ""}`;
}

export function getApiBase(): string {
  const publicApiUrl = readPublicRuntimeSetting("NEXT_PUBLIC_API_URL");
  if (publicApiUrl) return alignLoopbackUrlWithBrowser(publicApiUrl);
  return browserOriginWithPort(DEFAULT_BACKEND_PORT) || "http://localhost:8000";
}

export function getWsBase(): string {
  const publicWsUrl = readPublicRuntimeSetting("NEXT_PUBLIC_WS_URL");
  if (publicWsUrl) return alignLoopbackUrlWithBrowser(publicWsUrl);

  if (typeof window !== "undefined") {
    const { protocol, hostname, port } = window.location;
    if (hostname) {
      const wsProtocol = protocol === "https:" ? "wss:" : "ws:";
      const effectivePort = port || DEFAULT_BACKEND_PORT;
      return `${wsProtocol}//${hostname}${effectivePort ? `:${effectivePort}` : ""}`;
    }
  }

  return "ws://localhost:8000";
}

export const API_BASE = getApiBase();
export const WS_BASE = getWsBase();
