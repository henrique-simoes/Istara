/**
 * WebSocket connection manager with auto-reconnect.
 * Connects outbound — works through NAT and firewalls.
 */

import WebSocket from "ws";

const RECONNECT_DELAY_MS = 5000;
const MAX_RECONNECT_DELAY_MS = 60000;

export function createConnection(url, { token, networkToken, onOpen, onMessage, onClose, onError }) {
  let ws;
  let reconnectDelay = RECONNECT_DELAY_MS;
  let reconnectTimer = null;

  function connect() {
    const headers = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    // Send network access token for relay auth (if available from connection string)
    if (networkToken) {
      headers["X-Access-Token"] = networkToken;
    }

    ws = new WebSocket(url, { headers });

    ws.on("open", () => {
      reconnectDelay = RECONNECT_DELAY_MS;
      if (onOpen) onOpen();
    });

    ws.on("message", (data) => {
      if (onMessage) onMessage(data.toString());
    });

    ws.on("close", () => {
      if (onClose) onClose();
      scheduleReconnect();
    });

    ws.on("error", (err) => {
      if (onError) onError(err);
    });
  }

  function scheduleReconnect() {
    if (reconnectTimer) return;
    console.log(`🔄 Reconnecting in ${reconnectDelay / 1000}s...`);
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      reconnectDelay = Math.min(reconnectDelay * 1.5, MAX_RECONNECT_DELAY_MS);
      connect();
    }, reconnectDelay);
  }

  connect();

  // Return a proxy that always sends on the current ws
  return {
    send: (data) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    },
    close: () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (ws) ws.close();
    },
    get readyState() {
      return ws ? ws.readyState : WebSocket.CLOSED;
    },
  };
}
