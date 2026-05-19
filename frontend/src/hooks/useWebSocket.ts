"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { WSEvent } from "@/lib/types";
import { WS_BASE } from "@/lib/runtimeConfig";
import { useProjectStore } from "@/stores/projectStore";

const WS_URL = `${WS_BASE}/ws`;

export function useWebSocket(onEvent?: (event: WSEvent) => void) {
  const { activeProjectId } = useProjectStore();
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<"connecting" | "connected" | "reconnecting" | "disconnected" | "auth_failed">("connecting");
  const [lastCloseReason, setLastCloseReason] = useState("");
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  // Store callback in a ref so reconnect logic never depends on it
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    clearTimeout(reconnectTimer.current);

    // Append JWT token as query parameter for authentication
    const token = typeof window !== "undefined" ? localStorage.getItem("istara_token") : null;
    if (!token) {
      setConnected(false);
      setStatus("auth_failed");
      setLastCloseReason("Missing authentication token");
      reconnectTimer.current = setTimeout(connect, 3000);
      return;
    }
    setStatus("connecting");
    const params = new URLSearchParams({ token });
    if (activeProjectId) params.set("project_id", activeProjectId);
    const wsUrl = `${WS_URL}?${params.toString()}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnected(true);
      setStatus("connected");
      setLastCloseReason("");
      console.log("[Istara WS] Connected");
    };

    ws.onmessage = (event) => {
      try {
        const data: WSEvent = JSON.parse(event.data);
        if (data.type === "ping") {
          ws.send(JSON.stringify({ type: "pong" }));
          return;
        }
        onEventRef.current?.(data);
      } catch {
        // Skip malformed messages
      }
    };

    ws.onclose = (event) => {
      setConnected(false);
      const reason = event.reason || (event.code ? `Closed with code ${event.code}` : "");
      setLastCloseReason(reason);
      if (event.code === 4001 || event.code === 4003) {
        setStatus("auth_failed");
        console.log(`[Istara WS] Authentication failed. Retrying in 3s. ${reason}`);
        reconnectTimer.current = setTimeout(connect, 3000);
        return;
      }
      setStatus("reconnecting");
      console.log("[Istara WS] Disconnected. Reconnecting in 3s...");
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [activeProjectId]);

  useEffect(() => {
    connect();
    const handleAuthChanged = () => connect();
    window.addEventListener("storage", handleAuthChanged);
    window.addEventListener("istara:auth-changed", handleAuthChanged);
    return () => {
      clearTimeout(reconnectTimer.current);
      window.removeEventListener("storage", handleAuthChanged);
      window.removeEventListener("istara:auth-changed", handleAuthChanged);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((type: string, data: Record<string, unknown> = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...data }));
    }
  }, []);

  return { connected, status, lastCloseReason, send };
}
