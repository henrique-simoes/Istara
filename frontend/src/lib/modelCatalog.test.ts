import { describe, expect, it } from "vitest";

import { mergeModelCatalogs } from "./modelCatalog";
import { agentEngineLabel } from "./utils";

describe("merged model catalog", () => {
  it("keeps legacy switching and exposes deduplicated Pi identities", () => {
    const entries = mergeModelCatalogs(
      [{ name: "shared-model", provider_type: "ollama" }],
      [
        { endpoint_id: "pi-1", model: "shared-model", provider_kind: "openai_compat" },
        { endpoint_id: "pi-1", model: "shared-model", provider_kind: "openai_compat" },
        { endpoint_id: "pi-2", model: "pi-only", provider_kind: "anthropic_compat" },
      ],
    );

    expect(entries).toHaveLength(3);
    expect(entries[0]).toMatchObject({ name: "shared-model", engine: "legacy", switchable: true });
    expect(entries[1]).toMatchObject({
      name: "shared-model",
      endpoint_id: "pi-1",
      engine: "pi",
      switchable: false,
    });
    expect(entries[2]).toMatchObject({ name: "pi-only", endpoint_id: "pi-2", engine: "pi" });
  });

  it("ignores malformed catalog identities", () => {
    expect(mergeModelCatalogs([{}], [{ endpoint_id: "missing-model" }])).toEqual([]);
  });

  it("normalizes the global engine value used by inherited badges", () => {
    expect(agentEngineLabel(" PI-REPLACEMENT ")).toBe("Pi");
    expect(agentEngineLabel("legacy")).toBe("Istara");
  });
});
