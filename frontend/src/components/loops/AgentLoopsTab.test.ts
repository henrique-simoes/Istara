import { describe, expect, it } from "vitest";
import type { Agent, AgentLoopConfig } from "@/lib/types";
import { mergeProjectAgentLoops } from "./AgentLoopsTab";

const systemAgent = {
  id: "istara-main",
  name: "Istara",
  is_system: true,
} as Agent;

const projectAgent = {
  id: "researcher-1",
  name: "Researcher",
  is_system: false,
} as Agent;

const projectLoop = {
  id: "researcher-1",
  agent_id: "researcher-1",
} as AgentLoopConfig;

describe("mergeProjectAgentLoops", () => {
  it("does not expose controls for visible system agents without a project loop config", () => {
    expect(mergeProjectAgentLoops([systemAgent], [])).toEqual([]);
  });

  it("retains project agents that have a loop config", () => {
    expect(mergeProjectAgentLoops([projectAgent], [projectLoop])).toEqual([
      { agent: projectAgent, loopConfig: projectLoop },
    ]);
  });
});
