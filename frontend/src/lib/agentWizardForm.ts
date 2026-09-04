export const AGENT_HEARTBEAT_MIN_SECONDS = 10;
export const AGENT_HEARTBEAT_MAX_SECONDS = 3600;

export function isAgentHeartbeatValid(value: number | ""): value is number {
  return (
    typeof value === "number" &&
    Number.isInteger(value) &&
    value >= AGENT_HEARTBEAT_MIN_SECONDS &&
    value <= AGENT_HEARTBEAT_MAX_SECONDS
  );
}

export function agentHeartbeatError(value: number | ""): string | null {
  if (value === "") {
    return `Enter a heartbeat interval between ${AGENT_HEARTBEAT_MIN_SECONDS} and ${AGENT_HEARTBEAT_MAX_SECONDS} seconds.`;
  }
  return isAgentHeartbeatValid(value)
    ? null
    : `Heartbeat interval must be a whole number between ${AGENT_HEARTBEAT_MIN_SECONDS} and ${AGENT_HEARTBEAT_MAX_SECONDS} seconds.`;
}
