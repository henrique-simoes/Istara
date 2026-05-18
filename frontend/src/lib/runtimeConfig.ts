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

function browserOriginWithPort(port: string): string | null {
  if (typeof window === "undefined") return null;
  const { protocol, hostname } = window.location;
  if (!hostname) return null;
  return `${protocol}//${hostname}:${port}`;
}

export function getApiBase(): string {
  const publicApiUrl = readPublicRuntimeSetting("NEXT_PUBLIC_API_URL");
  if (publicApiUrl) return withoutTrailingSlash(publicApiUrl);
  return browserOriginWithPort(DEFAULT_BACKEND_PORT) || "http://localhost:8000";
}

export function getWsBase(): string {
  const publicWsUrl = readPublicRuntimeSetting("NEXT_PUBLIC_WS_URL");
  if (publicWsUrl) return withoutTrailingSlash(publicWsUrl);

  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    if (hostname) {
      const wsProtocol = protocol === "https:" ? "wss:" : "ws:";
      return `${wsProtocol}//${hostname}:${DEFAULT_BACKEND_PORT}`;
    }
  }

  return "ws://localhost:8000";
}

export const API_BASE = getApiBase();
export const WS_BASE = getWsBase();
