import assert from "node:assert/strict";
import test from "node:test";

import { buildChatTurns, buildTaskPlan, reviewerAssessment } from "./persona.mjs";

const sourceBackedTask = {
  title: "[RU-01] Analyze staff interview trust signals",
  description: "Extract staff evidence about readiness-status trust, source trails, and manual overrides.",
};

test("reviewerAssessment rejects blocked source-backed task output", () => {
  const assessment = reviewerAssessment(sourceBackedTask, `
    Status: Blocked.
    The required source documents could not be found, so confidence level: LOW.
    Source: 00-project-context.md
  `);

  assert.equal(assessment.approved, false);
  assert.ok(assessment.issues.some((issue) => issue.includes("blocked")));
  assert.ok(assessment.issues.some((issue) => issue.includes("low confidence")));
});

test("reviewerAssessment approves grounded task output with concrete sources", () => {
  const assessment = reviewerAssessment(sourceBackedTask, `
    Evidence: P04-nurse-manager.md says staff need the source trail before trusting readiness.
    Source: P06-care-coordinator.md shows manual override behavior when task state is unclear.
    Interpretation: both sources point to trust depending on visible evidence, because status alone is not enough.
    Recommendation: add readiness confidence labels.
    Confidence: medium.
  `);

  assert.equal(assessment.approved, true);
});

test("real-user benchmark chat turns and task prompts preserve realistic research depth", () => {
  const wordCount = (value) => String(value || "").trim().split(/\s+/).filter(Boolean).length;
  const chatTurns = buildChatTurns({ total: 20 });
  const taskPlan = buildTaskPlan({ total: 16 });

  assert.equal(chatTurns.length, 20);
  assert.equal(taskPlan.length, 16);
  assert.ok(chatTurns.every((turn) => wordCount(turn.content) >= 500));
  assert.ok(taskPlan.every((task) => wordCount(task.description) >= 500));
  assert.ok(chatTurns.every((turn) => /Research Spine|evidence units|reliability|Done/i.test(turn.content)));
  assert.ok(taskPlan.every((task) => /candidate atomic facts|reconciliation|report/i.test(task.description)));
});
