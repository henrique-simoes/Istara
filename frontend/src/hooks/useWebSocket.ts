"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { WSEvent } from "@/lib/types";
import { WS_BASE } from "@/lib/runtimeConfig";
import { useProjectStore } from "@/stores/projectStore";

const WS_URL = `${WS_BASE}/ws`;

const PROJECT_BOUND_EVENT_TYPES = new Set([
  "agent_created",
  "agent_created_from_proposal",
  "a2a_message",
  "agent_status",
  "agent_thinking",
  "agent_idle",
  "channel_message",
  "channel_status",
  "deployment_finding",
  "deployment_progress",
  "deployment_response",
  "document_created",
  "document_deleted",
  "document_updated",
  "file_processed",
  "finding_created",
  "meta_proposal",
  "plan_progress",
  "steering_message",
  "suggestion",
  "task_progress",
  "task_queue_update",
  "autoresearch_complete",
  "autoresearch_progress",
]);

function eventProjectId(event: WSEvent): string | null {
  const direct = event.data.project_id ?? event.data.projectId;
  if (typeof direct === "string" && direct.trim()) return direct.trim();
  const metadata = event.data.metadata;
  if (metadata && typeof metadata === "object" && !Array.isArray(metadata)) {
    const meta = metadata as Record<string, unknown>;
    const nested = meta.project_id ?? meta.projectId;
    if (typeof nested === "string" && nested.trim()) return nested.trim();
  }
  return null;
}

function shouldDeliverEvent(event: WSEvent, activeProjectId: string | null | undefined) {
  if (!PROJECT_BOUND_EVENT_TYPES.has(event.type)) return true;
  const projectId = eventProjectId(event);
  return Boolean(activeProjectId && projectId === activeProjectId);
}

export function useWebSocket(onEvent?: (event: WSEvent) => void) {
  const { activeProjectId } = useProjectStore();
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<"connecting" | "connected" | "reconnecting" | "disconnected" | "auth_failed">("connecting");
  const [lastCloseReason, setLastCloseReason] = useState("");
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const connectionVersion = useRef(0);
  const activeProjectIdRef = useRef(activeProjectId);
  activeProjectIdRef.current = activeProjectId;
  // Store callback in a ref so reconnect logic never depends on it
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN
      || wsRef.current?.readyState === WebSocket.CONNECTING
    ) return;
    clearTimeout(reconnectTimer.current);
    const version = ++connectionVersion.current;

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
      if (version !== connectionVersion.current) return;
      setConnected(true);
      setStatus("connected");
      setLastCloseReason("");
      console.log("[Istara WS] Connected");
    };

    ws.onmessage = (event) => {
      if (version !== connectionVersion.current) return;
      try {
        const data: WSEvent = JSON.parse(event.data);
        if (data.type === "ping") {
          ws.send(JSON.stringify({ type: "pong" }));
          return;
        }
        if (!shouldDeliverEvent(data, activeProjectIdRef.current)) return;
        onEventRef.current?.(data);
      } catch {
        // Skip malformed messages
      }
    };

    ws.onclose = (event) => {
      if (version !== connectionVersion.current) return;
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
      if (version !== connectionVersion.current) return;
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
      connectionVersion.current += 1;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  const send = useCallback((type: string, data: Record<string, unknown> = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...data }));
    }
  }, []);

  return { connected, status, lastCloseReason, send };
}
