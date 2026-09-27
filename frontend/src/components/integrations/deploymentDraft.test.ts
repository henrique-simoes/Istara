import { describe, expect, it } from "vitest";
import { buildDeploymentPayload, canLeaveStep, INITIAL_DRAFT } from "./deploymentDraft";

describe("deployment wizard draft", () => {
  it("asks for consent by default and sends the researcher's settings", () => {
    const payload = buildDeploymentPayload(
      {
        ...INITIAL_DRAFT,
        deploymentType: "interview",
        name: "Study",
        questions: [{ text: "Q1?", type: "open" }, { text: "  ", type: "open" }],
        screener: [{ text: "Weekly exporter?", accept: "yes, Yes " }, { text: " ", accept: "" }],
        closingQuestion: " Anything else? ",
        adaptiveEnabled: false,
      },
      "project-1"
    );
    expect(payload.questions).toEqual([{ text: "Q1?", type: "open" }]);
    expect(payload.config).toMatchObject({
      consent_required: true,
      adaptive_enabled: false,
      screener: [{ text: "Weekly exporter?", accept: ["yes", "Yes"] }],
      closing_question: "Anything else?",
      reminder_after_hours: 24,
      max_reminders: 1,
    });
    expect((payload.config.consent_message as string).length).toBeGreaterThan(20);
  });

  it("omits optional messages and reminders the researcher turned off", () => {
    const payload = buildDeploymentPayload(
      { ...INITIAL_DRAFT, deploymentType: "survey", remindersEnabled: false, consentRequired: false },
      "p"
    );
    expect(payload.config).not.toHaveProperty("intro_message");
    expect(payload.config).not.toHaveProperty("closing_question");
    expect(payload.config).toMatchObject({ consent_required: false, consent_message: "", max_reminders: 0 });
  });

  it("blocks Next until each step has what it needs", () => {
    expect(canLeaveStep("type", INITIAL_DRAFT)).toBe(false);
    expect(canLeaveStep("questions", INITIAL_DRAFT)).toBe(false);
    expect(canLeaveStep("participants", { ...INITIAL_DRAFT, consentMessage: " " })).toBe(false);
    expect(canLeaveStep("participants", { ...INITIAL_DRAFT, consentRequired: false, consentMessage: "" })).toBe(true);
    expect(canLeaveStep("channels", INITIAL_DRAFT)).toBe(false);
    expect(canLeaveStep("targets", { ...INITIAL_DRAFT, name: "Named" })).toBe(true);
  });
});
