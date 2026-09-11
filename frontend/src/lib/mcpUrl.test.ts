import { describe, expect, it } from "vitest";
import { isValidMcpServerUrl } from "./mcpUrl";

describe("isValidMcpServerUrl", () => {
  it("rejects malformed or non-http values before MCP actions are enabled", () => {
    expect(isValidMcpServerUrl("not-a-url")).toBe(false);
    expect(isValidMcpServerUrl("localhost:3001/mcp")).toBe(false);
    expect(isValidMcpServerUrl("file:///tmp/mcp")).toBe(false);
    expect(isValidMcpServerUrl("")).toBe(false);
  });

  it("accepts absolute HTTP(S) endpoints without credentials or queries", () => {
    expect(isValidMcpServerUrl("http://localhost:3001/mcp")).toBe(true);
    expect(isValidMcpServerUrl("https://mcp.example.test/v1")).toBe(true);
    expect(isValidMcpServerUrl("https://user:pass@mcp.example.test/v1")).toBe(false);
    expect(isValidMcpServerUrl("https://mcp.example.test/v1?token=secret")).toBe(false);
  });
});
