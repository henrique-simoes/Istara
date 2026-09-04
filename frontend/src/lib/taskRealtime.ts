import type { WSEvent } from "./types";

export function shouldRefreshKanbanForEvent(event: Pick<WSEvent, "type" | "data">): boolean {
  if (event.type === "task_queue_update") return true;
  if (event.type !== "task_progress") return false;

  const progress = Number(event.data.progress || 0);
  const outcome = String(event.data.outcome || "").trim();
  return progress >= 1 || Boolean(outcome);
}
