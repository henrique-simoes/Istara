import { describe, expect, it } from "vitest";

import {
  ENGINE_COMPARATIVE_SUMMARIES,
  ENGINE_SELECTOR_OPTIONS,
  SHARED_EMBEDDING_IDENTITY_LABEL,
  mergeModelCatalogs,
} from "./modelCatalog";
import { agentEngineLabel } from "./utils";

describe("engine comparative summaries (W3 selector slice)", () => {
  it("covers exactly the two canonical engines with provisional, provenance-cited summaries", () => {
    expect(ENGINE_COMPARATIVE_SUMMARIES.map((e) => e.engine).sort()).toEqual([
      "legacy",
      "pi",
    ]);
    expect(ENGINE_SELECTOR_OPTIONS).toEqual(["pi", "legacy"]);
    for (const entry of ENGINE_COMPARATIVE_SUMMARIES) {
      expect(entry.title.length).toBeGreaterThan(0);
      expect(entry.summary.length).toBeGreaterThan(20);
      // Every selector summary must stay provisional — comparative model prose
      // is never presented as accepted research evidence.
      expect(entry.provisional).toBe(true);
      // Every claim must carry evidence provenance the reader can verify.
      expect(entry.provenance.length).toBeGreaterThan(0);
      expect(entry.provenance[0]).toMatch(/comparison-Istara-pi\/reports\//);
      expect(entry.asOf.length).toBeGreaterThan(0);
    }
  });

  it("does not fabricate a winner: summaries cite the no-significant-difference verdict", () => {
    for (const entry of ENGINE_COMPARATIVE_SUMMARIES) {
      expect(entry.summary).toMatch(/no judged axis reaches significance at 95% CI/);
      expect(entry.summary).not.toMatch(/outperforms|is better than|faster than/i);
    }
  });

  it("describes Istara as a loop mode over shared Pi Model Management authority", () => {
    const istara = ENGINE_COMPARATIVE_SUMMARIES.find((entry) => entry.engine === "legacy");

    expect(istara).toBeDefined();
    expect(istara?.summary).toMatch(/shared Pi Model Management catalog/);
    expect(istara?.shortDescription).toMatch(/shared Pi Model Management catalog/);
    expect(istara?.bestFor).toMatch(/governed catalog/);
    expect(istara?.summary).not.toMatch(/ComputeRegistry\/Ollama plane|legacy plane/i);
    expect(istara?.shortDescription).not.toMatch(/ComputeRegistry|legacy plane/i);
  });

  it("exposes one shared embedding identity that engine switching cannot change", () => {
    expect(SHARED_EMBEDDING_IDENTITY_LABEL).toMatch(/never changes the embedding space/);
  });
});

describe("merged model catalog", () => {
  it("keeps every compatibility inventory row non-switchable under Pi authority", () => {
    const entries = mergeModelCatalogs(
      [{ name: "classical-row", provider_type: "ollama" }],
      [{ endpoint_id: "pi-1", model: "pi-row", provider_kind: "openai_compat" }],
    );

    expect(entries).toHaveLength(2);
    expect(entries.every((entry) => entry.switchable === false)).toBe(true);
  });

  it("exposes deduplicated compatibility and Pi identities without mutation authority", () => {
    const entries = mergeModelCatalogs(
      [{ name: "shared-model", provider_type: "ollama" }],
      [
        { endpoint_id: "pi-1", model: "shared-model", provider_kind: "openai_compat" },
        { endpoint_id: "pi-1", model: "shared-model", provider_kind: "openai_compat" },
        { endpoint_id: "pi-2", model: "pi-only", provider_kind: "anthropic_compat" },
      ],
    );

    expect(entries).toHaveLength(3);
    expect(entries[0]).toMatchObject({ name: "shared-model", engine: "legacy", switchable: false });
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
