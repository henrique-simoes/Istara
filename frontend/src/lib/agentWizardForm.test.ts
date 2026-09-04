import { describe, expect, it } from "vitest";
import {
  AGENT_HEARTBEAT_MAX_SECONDS,
  AGENT_HEARTBEAT_MIN_SECONDS,
  agentHeartbeatError,
  isAgentHeartbeatValid,
} from "./agentWizardForm";

describe("agent wizard heartbeat validation", () => {
  it("accepts the backend contract bounds", () => {
    expect(isAgentHeartbeatValid(AGENT_HEARTBEAT_MIN_SECONDS)).toBe(true);
    expect(isAgentHeartbeatValid(AGENT_HEARTBEAT_MAX_SECONDS)).toBe(true);
  });

  it.each(["", 0, 9, 3_601, 1.5])("rejects an invalid heartbeat %s", (value) => {
    expect(isAgentHeartbeatValid(value as number | "")).toBe(false);
    expect(agentHeartbeatError(value as number | "")).toBeTruthy();
  });

  it("returns no error for a valid heartbeat", () => {
    expect(agentHeartbeatError(60)).toBeNull();
  });
});
