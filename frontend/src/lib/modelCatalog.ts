export interface MergedModelCatalogEntry {
  name: string;
  engine: "legacy" | "pi";
  switchable: boolean;
  provider_type?: string;
  server_name?: string;
  endpoint_id?: string;
  size?: number;
  [key: string]: unknown;
}

/**
 * Evidence-backed, provisional comparative summary for the engine selector.
 *
 * The summary text is grounded in the accepted Pi-vs-Istara benchmark bundle
 * (``comparison-Istara-pi/reports/20260801T010602Z/scorecard.json``, verdict
 * ``no_significant_difference``: no judged axis reaches significance at 95%
 * CI). It stays PROVISIONAL — comparative model prose is never treated as
 * accepted research evidence (Research Spine contract) — and always carries
 * its provenance so readers can verify the claim at the source.
 */
export interface EngineComparativeSummary {
  engine: "pi" | "legacy";
  /** Short headline for the option. */
  title: string;
  /** Concise, evidence-backed summary shown in the selector. */
  summary: string;
  /** Evidence provenance: repo-relative artifacts that back the summary. */
  provenance: string[];
  /** Benchmark bundle timestamp the summary is grounded in. */
  asOf: string;
  /** Always true for selector summaries: never presented as accepted evidence. */
  provisional: boolean;
  shortDescription: string;
  bestFor: string;
  benchmarkRows: Array<{ label: string; value: string }>;
}

const ENGINE_BENCHMARK_BUNDLE = "comparison-Istara-pi/reports/20260801T010602Z/scorecard.json";

/**
 * One shared, canonical embedding identity for both engines. The selector
 * must never offer a per-engine embedding model: switching engines cannot
 * change the vector space (W8 invariant), so the UI surfaces this identity as
 * safe metadata (model name only — never an endpoint, URL, or key).
 */
export const SHARED_EMBEDDING_IDENTITY_LABEL =
  "Both engines embed with the same configured model; switching engines never changes the embedding space.";

export const ENGINE_COMPARATIVE_SUMMARIES: EngineComparativeSummary[] = [
  {
    engine: "pi",
    title: "Pi",
    summary:
      "Standalone agent runtime (pi-agent-core worker) with versioned wire protocol, provider catalog, and forced structured-output tool calls. In the accepted benchmark bundle no judged axis reaches significance at 95% CI: tool calling 0.81 vs 0.83, output quality 6.75 vs 6.64, research-spine 1.00 vs 0.81, skills/A2A tied at 1.00.",
    provenance: [ENGINE_BENCHMARK_BUNDLE, "docs/features/content/chat/model-controls/architecture.md"],
    asOf: "2026-08-01",
    provisional: true,
    shortDescription: "A standalone, versioned agent runtime with a broad provider catalog and structured tool execution.",
    bestFor: "Cloud providers, exact model/effort controls, and governed tool workflows.",
    benchmarkRows: [
      { label: "Tool calling", value: "0.81" },
      { label: "Output quality", value: "6.75 / 10" },
      { label: "Research-spine", value: "1.00" },
      { label: "Skills / A2A", value: "1.00" },
    ],
  },
  {
    engine: "legacy",
    title: "Istara",
    summary:
      "In-process legacy executor over the ComputeRegistry/Ollama plane used across Istara. In the accepted benchmark bundle no judged axis reaches significance at 95% CI: tool calling 0.83 vs 0.81, output quality 6.64 vs 6.75, research-spine 0.81 vs 1.00, skills/A2A tied at 1.00.",
    provenance: [ENGINE_BENCHMARK_BUNDLE, "docs/features/content/chat/model-controls/architecture.md"],
    asOf: "2026-08-01",
    provisional: true,
    shortDescription: "Istara's in-process executor over the existing ComputeRegistry and local/server model plane.",
    bestFor: "Local models, donated compute, and workflows already attached to the legacy plane.",
    benchmarkRows: [
      { label: "Tool calling", value: "0.83" },
      { label: "Output quality", value: "6.64 / 10" },
      { label: "Research-spine", value: "0.81" },
      { label: "Skills / A2A", value: "1.00" },
    ],
  },
];

/** Canonical engine option ids for the selector (values the backend accepts). */
export const ENGINE_SELECTOR_OPTIONS = ["pi", "legacy"] as const;

/**
 * Present both routing planes in the existing Settings model inventory.
 * Pi entries are identity-only and therefore intentionally not switchable by
 * the legacy provider switch endpoint.
 */
export function mergeModelCatalogs(
  legacyModels: unknown[] | null | undefined,
  piCatalog: unknown[] | null | undefined,
): MergedModelCatalogEntry[] {
  const merged: MergedModelCatalogEntry[] = [];
  const seenLegacy = new Set<string>();
  const seenPi = new Set<string>();

  for (const raw of legacyModels || []) {
    if (!raw || typeof raw !== "object") continue;
    const model = raw as Record<string, unknown>;
    const name = String(model.name || model.model || "").trim();
    if (!name) continue;
    const key = `${name}\u0000${String(model.server_name || model.provider_type || "")}`;
    if (seenLegacy.has(key)) continue;
    seenLegacy.add(key);
    merged.push({ ...model, name, engine: "legacy", switchable: true });
  }

  for (const raw of piCatalog || []) {
    if (!raw || typeof raw !== "object") continue;
    const model = raw as Record<string, unknown>;
    const name = String(model.model || model.name || "").trim();
    const endpointId = String(model.endpoint_id || "").trim();
    if (!name || !endpointId || seenPi.has(endpointId)) continue;
    seenPi.add(endpointId);
    merged.push({
      ...model,
      name,
      endpoint_id: endpointId,
      provider_type: String(model.provider_kind || model.provider_type || ""),
      server_name: endpointId,
      engine: "pi",
      switchable: false,
    });
  }

  return merged;
}
