/**
 * Check the URL shape accepted by the MCP client registration API.
 * Host policy (for example, public HTTP versus HTTPS) remains enforced by
 * the backend endpoint-security policy; this helper prevents malformed input
 * from enabling actions that would only fail after a request is sent.
 */
export function isValidMcpServerUrl(rawUrl: string): boolean {
  const value = rawUrl.trim();
  if (!value) return false;

  try {
    const parsed = new URL(value);
    return (
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
      Boolean(parsed.hostname) &&
      !parsed.username &&
      !parsed.password &&
      !parsed.search
    );
  } catch {
    return false;
  }
}

export function mcpServerUrlError(rawUrl: string): string | null {
  if (!rawUrl.trim() || isValidMcpServerUrl(rawUrl)) return null;
  return "Enter an absolute http(s) URL without credentials or query parameters.";
}
