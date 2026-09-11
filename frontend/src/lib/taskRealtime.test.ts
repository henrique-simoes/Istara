import { describe, expect, it } from "vitest";

import { shouldRefreshKanbanForEvent } from "./taskRealtime";

describe("Kanban realtime reconciliation", () => {
  it("refreshes for queue snapshots and terminal task outcomes", () => {
    expect(shouldRefreshKanbanForEvent({ type: "task_queue_update", data: {} })).toBe(true);
    expect(shouldRefreshKanbanForEvent({
      type: "task_progress",
      data: { progress: 1, outcome: "verification_failed" },
    })).toBe(true);
    expect(shouldRefreshKanbanForEvent({
      type: "task_progress",
      data: { progress: 0.3 },
    })).toBe(false);
  });
});
