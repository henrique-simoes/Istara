import { describe, expect, it } from "vitest";
import { describeNextRuns } from "./CronBuilder";

describe("describeNextRuns", () => {
  it("returns five future runs for a daily schedule", () => {
    const runs = describeNextRuns("0 9 * * *");

    expect(runs).toHaveLength(5);
    expect(runs).not.toContain("Unable to compute next runs");
  });

  it("returns five future runs for a weekly schedule", () => {
    const runs = describeNextRuns("0 9 * * 1");

    expect(runs).toHaveLength(5);
    expect(runs).not.toContain("Unable to compute next runs");
  });

  it("does not present a partial list for an impossible expression", () => {
    expect(describeNextRuns("0 9 31 2 *")).toEqual(["Unable to compute next runs"]);
  });
});
