import { describe, expect, it } from "vitest";

import {
  classifyAgentStatusToast,
  classifyTaskProgressToast,
} from "./taskProgressToast";

describe("classifyTaskProgressToast", () => {
  it("shows verification failure as a warning instead of completed work", () => {
    expect(
      classifyTaskProgressToast({
        progress: 1,
        notes: "Verification failed: No candidate evidence proposed.",
        outcome: "verification_failed",
      })
    ).toEqual({
      type: "warning",
      title: "⚠️ Task Needs Attention",
      message: "Verification failed: No candidate evidence proposed.",
    });
  });

  it("keeps legacy verification-failure events truthful without an outcome", () => {
    expect(
      classifyTaskProgressToast({
        progress: 1,
        notes: "Verification failed: response too short",
      })
    ).toMatchObject({ type: "warning", title: "⚠️ Task Needs Attention" });
  });

  it("describes verified terminal work as ready for review", () => {
    expect(
      classifyTaskProgressToast({
        progress: 1,
        notes: "Complete — ready for review.",
        outcome: "ready_for_review",
      })
    ).toEqual({
      type: "success",
      title: "✅ Ready for Review",
      message: "Complete — ready for review.",
    });
  });

  it("does not infer success from an unclassified 100 percent event", () => {
    expect(classifyTaskProgressToast({ progress: 1, notes: "Final update" })).toEqual({
      type: "info",
      title: "ℹ️ Task Update",
      message: "Final update",
    });
  });

  it("does not toast intermediate progress", () => {
    expect(classifyTaskProgressToast({ progress: 0.8, notes: "Verifying" })).toBeNull();
  });
});

describe("classifyAgentStatusToast", () => {
  it("surfaces warning status as needs-attention guidance", () => {
    expect(classifyAgentStatusToast("warning", "Needs attention: task")).toEqual({
      type: "warning",
      title: "⚠️ Agent Needs Attention",
      message: "Needs attention: task",
    });
  });
});
