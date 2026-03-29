/**
 * Connection string decoder for the relay daemon.
 *
 * Format: rcl_<base64url(JSON)>.<base64url(HMAC)>
 *
 * The relay doesn't verify the HMAC (it doesn't have the server secret).
 * The server validates the tokens when the relay connects.
 */

const PREFIX = "rcl_";

/**
 * Decode a base64url string to a regular string.
 */
function b64decode(s) {
  // Add padding
  const padding = 4 - (s.length % 4);
  if (padding !== 4) s += "=".repeat(padding);
  return Buffer.from(s.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString("utf8");
}

/**
 * Decode a connection string.
 * Returns { serverUrl, wsUrl, networkToken, jwt, label, expiresAt } or null.
 */
export function decodeConnectionString(connStr) {
  if (!connStr || !connStr.startsWith(PREFIX)) {
    return null;
  }

  try {
    const body = connStr.slice(PREFIX.length);
    const parts = body.split(".");
    if (parts.length !== 2) return null;

    const [payloadB64] = parts;
    const payload = JSON.parse(b64decode(payloadB64));

    if (payload.v !== 1) return null;

    // Check expiry
    if (payload.expires_at && payload.expires_at < Date.now() / 1000) {
      console.error("Connection string has expired");
      return null;
    }

    return {
      serverUrl: payload.server_url || "",
      wsUrl: payload.ws_url || "",
      networkToken: payload.network_token || "",
      jwt: payload.jwt || "",
      label: payload.label || "",
      expiresAt: payload.expires_at || 0,
    };
  } catch (err) {
    console.error("Failed to decode connection string:", err.message);
    return null;
  }
}
