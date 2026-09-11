import { beforeEach, describe, expect, it, vi } from "vitest";

const createSchedule = vi.fn();
const schedules = vi.fn();
const health = vi.fn();

vi.mock("@/lib/api", () => ({
  loops: {
    createSchedule,
    schedules,
    health,
  },
}));

describe("loops store schedule creation", () => {
  beforeEach(() => {
    createSchedule.mockReset();
    schedules.mockReset().mockResolvedValue([]);
    health.mockReset().mockResolvedValue([]);
  });

  it("returns success after creating and refreshing a schedule", async () => {
    createSchedule.mockResolvedValue({ id: "schedule-1" });
    const { useLoopsStore } = await import("./loopsStore");

    await expect(useLoopsStore.getState().createSchedule({
      name: "Daily scan",
      skill_name: "ux_evaluation",
      project_id: "project-1",
      cron_expression: "0 9 * * *",
    })).resolves.toBe(true);

    expect(schedules).toHaveBeenCalledWith("project-1");
    expect(health).toHaveBeenCalledWith("project-1");
    expect(useLoopsStore.getState().error).toBeNull();
  });

  it("returns failure and preserves the error when the API rejects", async () => {
    createSchedule.mockRejectedValue(new Error("Invalid cron expression"));
    const { useLoopsStore } = await import("./loopsStore");

    await expect(useLoopsStore.getState().createSchedule({
      name: "Impossible date",
      skill_name: "ux_evaluation",
      project_id: "project-1",
      cron_expression: "0 * 31 2 *",
    })).resolves.toBe(false);

    expect(schedules).not.toHaveBeenCalled();
    expect(health).not.toHaveBeenCalled();
    expect(useLoopsStore.getState().error).toBe("Invalid cron expression");
  });
});
