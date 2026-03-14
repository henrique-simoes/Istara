"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { WSEvent } from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

export function useWebSocket(onEvent?: (event: WSEvent) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setConnected(true);
      console.log("[ReClaw WS] Connected");
    };

    ws.onmessage = (event) => {
      try {
        const data: WSEvent = JSON.parse(event.data);
        if (data.type === "ping") {
          ws.send(JSON.stringify({ type: "pong" }));
          return;
        }
        onEvent?.(data);
      } catch {
        // Skip malformed messages
      }
    };

    ws.onclose = () => {
      setConnected(false);
      console.log("[ReClaw WS] Disconnected. Reconnecting in 3s...");
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [onEvent]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((type: string, data: Record<string, unknown> = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...data }));
    }
  }, []);

  return { connected, send };
}
