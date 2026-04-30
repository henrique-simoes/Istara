const DEFAULT_BACKEND_PORT = "8000";

function browserOriginWithPort(port: string): string | null {
  if (typeof window === "undefined") return null;
  const { protocol, hostname } = window.location;
  if (!hostname) return null;
  return `${protocol}//${hostname}:${port}`;
}

export function getApiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");
  return browserOriginWithPort(DEFAULT_BACKEND_PORT) || "http://localhost:8000";
}

export function getWsBase(): string {
  const configured = process.env.NEXT_PUBLIC_WS_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");

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
