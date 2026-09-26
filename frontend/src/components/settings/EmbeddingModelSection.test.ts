import { describe, expect, it } from "vitest";
import { explainStartError, migrationSummary, schemeLabel } from "./EmbeddingModelSection";

describe("EmbeddingModelSection messages", () => {
  it("names the prompt scheme, and says when there are none", () => {
    expect(schemeLabel("raw")).toBe("raw text (no prompts)");
    expect(schemeLabel("embeddinggemma")).toBe("embeddinggemma prompts");
  });

  it("reports progress, completion and a resumable failure", () => {
    expect(migrationSummary(null)).toBeNull();
    expect(migrationSummary({ state: "idle" })).toBeNull();
    expect(
      migrationSummary({ state: "running", model_id: "embeddinggemma", stores_done: 1, stores_total: 3, rows_reembedded: 40 })
    ).toEqual({ tone: "progress", text: "Re-indexing with embeddinggemma: 1 of 3 tables, 40 chunks re-embedded." });
    expect(
      migrationSummary({ state: "done", model_id: "embeddinggemma", stores_done: 2, stores_skipped: 1, rows_reembedded: 70 })
    ).toEqual({ tone: "done", text: "Now using embeddinggemma: 2 tables re-embedded (70 chunks), 1 already current." });
    const failed = migrationSummary({ state: "failed", error: "RuntimeError: disk full" });
    expect(failed?.tone).toBe("failed");
    expect(failed?.text).toContain("disk full");
    expect(failed?.text).toContain("Run it again");
  });

  it("explains a refused start in the researcher's terms", () => {
    expect(explainStartError("embedding_model_unavailable: model 'x' not found")).toBe(
      "That model could not embed, so nothing changed (embedding_model_unavailable: model 'x' not found)."
    );
    expect(explainStartError("migration_already_running")).toBe(
      "A re-index is already running; wait for it to finish."
    );
    expect(explainStartError("Admin access required")).toBe("Admin access required");
  });
});
