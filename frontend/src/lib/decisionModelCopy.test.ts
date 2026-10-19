import { describe, expect, it } from "vitest";
import {
  ASSURANCE_MODE_COPY,
  decisionModelErrorMessage,
  isAliasModelId,
} from "./decisionModelCopy";

describe("decision-model copy", () => {
  it("flags moving aliases the way the backend does", () => {
    expect(isAliasModelId("jev-latest")).toBe(true);
    expect(isAliasModelId(" JEV-Preview ")).toBe(true);
    expect(isAliasModelId("latest")).toBe(true);
    expect(isAliasModelId("jev-1.14.0")).toBe(false);
    expect(isAliasModelId("")).toBe(false);
  });

  it("turns API refusal codes into plain language and keeps unknown messages", () => {
    expect(decisionModelErrorMessage(new Error("hosted_decider_needs_egress_opt_in"), "x")).toMatch(
      /allow this project/
    );
    expect(decisionModelErrorMessage(new Error("Server exploded"), "x")).toBe("Server exploded");
    expect(decisionModelErrorMessage(null, "fallback")).toBe("fallback");
  });

  it("says human review is required, and that both never merges votes", () => {
    expect(ASSURANCE_MODE_COPY.none.body).toMatch(/Human review is required/);
    expect(ASSURANCE_MODE_COPY.both.body).toMatch(/never merged/);
  });
});
