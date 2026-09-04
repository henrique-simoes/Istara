import { describe, expect, it } from "vitest";
import { formatAgentOnboardingDescription } from "./AgentsView";

describe("formatAgentOnboardingDescription", () => {
  it("keeps the onboarding copy aligned with the rendered system-agent count", () => {
    expect(formatAgentOnboardingDescription(6)).toContain("6 system agents handle research tasks");
  });
});
