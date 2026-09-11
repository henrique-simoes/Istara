import { describe, expect, it } from "vitest";

import {
  ENGINE_COMPARATIVE_SUMMARIES,
  ENGINE_SELECTOR_OPTIONS,
  SHARED_EMBEDDING_IDENTITY_LABEL,
  buildChatModelChoices,
  isPiEndpointReady,
  isPiSessionOverrideReady,
  mergeModelCatalogs,
  normalizeProviderId,
  resolveCatalogListState,
  resolveChatModelChoice,
  settingsDefaultChatModel,
  settingsLlmReadiness,
  isChatSendReady,
} from "./modelCatalog";
import { agentEngineLabel } from "./utils";
import type { PiEndpointInfo } from "./types";

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

  it("carries the dated 150-turn long-horizon slice as neutral per-engine rows", () => {
    // Readiness5 Wave W4 (2026-09-11): same model both engines
    // (glm-5.3-flash), 151 recorded turns each, reliability parity.
    // Rows stay neutral medians/counts — never a winner claim.
    for (const entry of ENGINE_COMPARATIVE_SUMMARIES) {
      const labels = entry.benchmarkRows.map((row) => row.label);
      expect(labels).toContain("150-turn median (2026-09-11)");
      expect(labels).toContain("150-turn success (2026-09-11)");
      expect(labels).toContain("150-turn cost (2026-09-11)");
      expect(labels).toContain("150-turn tools (2026-09-11)");
      const success = entry.benchmarkRows.find(
        (row) => row.label === "150-turn success (2026-09-11)",
      );
      expect(success?.value).toBe("151/151");
      // The slice is appended provenance, never a replacement of the bundle.
      expect(entry.provenance[0]).toMatch(/comparison-Istara-pi\/reports\//);
      expect(entry.provenance).toContain(
        "docs/build-stream/w4-long-horizon-telemetry-20260911.json",
      );
      expect(entry.summary).toMatch(/150-turn long-horizon slice \(2026-09-11/);
      expect(entry.summary).not.toMatch(/outperforms|is better than|faster than/i);
    }
    const pi = ENGINE_COMPARATIVE_SUMMARIES.find((entry) => entry.engine === "pi");
    const legacy = ENGINE_COMPARATIVE_SUMMARIES.find((entry) => entry.engine === "legacy");
    expect(
      pi?.benchmarkRows.find((row) => row.label === "150-turn median (2026-09-11)")?.value,
    ).toBe("18.7 s");
    expect(
      legacy?.benchmarkRows.find((row) => row.label === "150-turn median (2026-09-11)")?.value,
    ).toBe("21.3 s");
    expect(
      pi?.benchmarkRows.find((row) => row.label === "150-turn cost (2026-09-11)")?.value,
    ).toBe("$0.31 metered");
    expect(
      legacy?.benchmarkRows.find((row) => row.label === "150-turn cost (2026-09-11)")?.value,
    ).toBe("unmetered");
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
  it("keeps chat send fail-closed until the selected legacy transport is ready", () => {
    expect(isChatSendReady("legacy", false)).toBe(false);
    expect(isChatSendReady("legacy", undefined)).toBe(false);
    expect(isChatSendReady("legacy", true)).toBe(true);
    expect(isChatSendReady("pi", false)).toBe(true);
  });

  it("distinguishes transport reachability from chat readiness in Settings", () => {
    expect(settingsLlmReadiness({ reachable: false, chat_ready: false })).toBe("disconnected");
    expect(settingsLlmReadiness({ reachable: true, chat_ready: false })).toBe("not_ready");
    expect(settingsLlmReadiness({ reachable: true, chat_ready: true })).toBe("ready");
  });

  it("does not present the local transport model as the Pi chat default", () => {
    expect(
      settingsDefaultChatModel(
        {
          agentic_engine_default: "pi",
          default_model: null,
          active_model: "contract-stub-model",
        },
        { agentic_engine_default: "pi" },
      ),
    ).toBeNull();
    expect(
      settingsDefaultChatModel(
        { agentic_engine_default: "legacy", active_model: "contract-stub-model" },
        {
          agentic_engine_default: "legacy",
          llm_readiness: { reachable: true, chat_ready: false },
        },
      ),
    ).toBeNull();
    expect(
      settingsDefaultChatModel(
        { agentic_engine_default: "legacy", active_model: "local-ready-model" },
        {
          agentic_engine_default: "legacy",
          llm_readiness: { reachable: true, chat_ready: true },
        },
      ),
    ).toBe("local-ready-model");
  });

  it("enables only endpoints the server has resolved as credential-ready", () => {
    expect(isPiEndpointReady({ credential_status: "ready" })).toBe(true);
    expect(isPiEndpointReady({ credential_status: "missing" })).toBe(false);
    expect(isPiEndpointReady({ credential_status: "unavailable" })).toBe(false);
    expect(isPiEndpointReady({})).toBe(false);
  });

  it("does not let a stale session override re-enable an unavailable Pi endpoint", () => {
    const configured = [
      {
        endpoint_id: "pi-deepseek-default",
        model: "deepseek-v4-pro",
        credential_status: "missing",
      },
      {
        endpoint_id: "pi-ready",
        model: "ready-model",
        credential_status: "ready",
      },
    ];

    expect(
      isPiSessionOverrideReady(configured, "deepseek-v4-pro", "pi-deepseek-default"),
    ).toBe(false);
    expect(isPiSessionOverrideReady(configured, "ready-model", "pi-ready")).toBe(true);
    expect(isPiSessionOverrideReady(configured, "ready-model", "missing-endpoint")).toBe(false);
  });

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

describe("inherited capability carry-through (pi-compat W3)", () => {
  it("passes the tier-4 authority fields through to chat choices untouched", () => {
    // The menu consumes emitted thinkingLevels as given (DEC-M2 — the filter
    // is never reimplemented client-side); thinkingLevelMap/compat ride the
    // same record. This pins the payload contract against a consumer that
    // strips or reshapes the inherited fields.
    const provider = {
      id: "zai",
      display_name: "Zai",
      login_methods: ["api_key"],
      oauth_flow: null,
      env_var: "ZAI_API_KEY",
      auth_json_key: null,
      base_url: null,
      models: [
        {
          id: "glm-5.3",
          name: "GLM-5.3",
          api: "openai-completions",
          reasoning: true,
          thinkingLevels: ["low", "high", "max"],
          thinkingLevelMap: { off: null, minimal: null, low: "low", medium: null, high: "high", xhigh: null, max: "max" },
          compat: { thinkingFormat: "zai", supportsReasoningEffort: true },
        },
      ],
    } as any;
    const configured: PiEndpointInfo[] = [
      { endpoint_id: "pi-zai-glm53", model: "glm-5.3", provider_kind: "openai_compat", pi_provider: "zai", credential_status: "ready" },
    ];
    const choices = buildChatModelChoices({
      providers: [provider],
      configured,
      legacyModels: [],
      engine: "pi",
    });
    const choice = choices.find((c) => c.modelId === "glm-5.3");
    expect(choice?.model?.thinkingLevels).toEqual(["low", "high", "max"]);
    expect(choice?.model?.thinkingLevelMap?.max).toBe("max");
    expect(choice?.model?.compat?.supportsReasoningEffort).toBe(true);
  });

  it("keeps mapless overlay models on the fallback menu shape", () => {
    // Governed overlays carry null authority fields; the menu must fall back
    // instead of rendering an empty/non-array level list.
    const provider = {
      id: "dashscope",
      display_name: "DashScope",
      login_methods: ["api_key"],
      oauth_flow: null,
      env_var: "DASHSCOPE_API_KEY",
      auth_json_key: null,
      base_url: null,
      models: [{ id: "glm-5.1", name: "GLM-5.1", api: "openai-completions", reasoning: true, thinkingLevelMap: null, compat: null }],
    } as any;
    const choices = buildChatModelChoices({
      providers: [provider],
      configured: [],
      legacyModels: [],
      engine: "pi",
    });
    expect(choices[0]?.model?.thinkingLevelMap).toBeNull();
    expect(choices[0]?.model?.compat).toBeNull();
  });
});

describe("chat model choices (CF-SPEC-14)", () => {
  const providers = [
    {
      id: "openai-codex",
      display_name: "OpenAI Codex",
      login_methods: ["oauth"],
      oauth_flow: null,
      env_var: null,
      auth_json_key: null,
      base_url: null,
      models: [
        { id: "gpt-5.6-luna", name: "Luna", api: "openai-codex-responses", thinkingLevels: ["low", "high"] },
      ],
    },
    {
      id: "zai",
      display_name: "Zai",
      login_methods: ["api_key"],
      oauth_flow: null,
      env_var: "ZAI_API_KEY",
      auth_json_key: null,
      base_url: null,
      models: [{ id: "glm-5.2", name: "GLM 5.2", api: "openai-compatible" }],
    },
  ];

  const configured: PiEndpointInfo[] = [
    { endpoint_id: "pi-codex-luna", model: "gpt-5.6-luna", provider_kind: "openai_codex", pi_provider: "openai-codex", credential_status: "ready" },
    { endpoint_id: "pi-zai-glm", model: "glm-5.3-flash", provider_kind: "openai_compat", pi_provider: "zai", credential_status: "ready" },
    { endpoint_id: "pi-local", model: "custom-local:latest", provider_kind: "openai_compat", pi_provider: "", credential_status: "ready" },
    { endpoint_id: "pi-dead", model: "glm-5.2", provider_kind: "openai_compat", pi_provider: "zai", credential_status: "missing" },
  ];

  it("normalizes provider ids across underscore/dash spellings", () => {
    expect(normalizeProviderId("openai_codex")).toBe("openai-codex");
    expect(normalizeProviderId(" OpenAI-Codex ")).toBe("openai-codex");
  });

  it("matches endpoints by normalized provider id with provider_kind fallback", () => {
    const choices = buildChatModelChoices({ providers, configured, legacyModels: [], engine: "pi" });
    const luna = choices.find((c) => c.endpointId === "pi-codex-luna");
    // provider_kind openai_codex normalizes to the openai-codex catalog row
    expect(luna?.enabled).toBe(true);
    expect(luna?.configured).toBe(true);
  });

  it("surfaces ready endpoints missing from the catalog as standalone enabled choices", () => {
    const choices = buildChatModelChoices({ providers, configured, legacyModels: [], engine: "pi" });
    const zai = choices.find((c) => c.endpointId === "pi-zai-glm");
    const local = choices.find((c) => c.endpointId === "pi-local");
    expect(zai?.enabled).toBe(true);
    expect(zai?.configured).toBe(true);
    expect(local?.enabled).toBe(true);
    expect(local?.configured).toBe(true);
    // Ready choices sort before disabled catalog rows.
    const firstDisabled = choices.findIndex((c) => !c.enabled);
    expect(choices.findIndex((c) => c.endpointId === "pi-zai-glm")).toBeLessThan(firstDisabled);
  });

  it("keeps missing-credential endpoints disabled", () => {
    const choices = buildChatModelChoices({ providers, configured, legacyModels: [], engine: "pi" });
    const dead = choices.filter((c) => c.endpointId === "pi-dead");
    expect(dead.length).toBeGreaterThan(0);
    expect(dead.every((c) => c.enabled === false)).toBe(true);
  });

  it("prefers the default endpoint and falls back to the first enabled choice", () => {
    const choices = buildChatModelChoices({ providers, configured, legacyModels: [], engine: "pi" });
    expect(resolveChatModelChoice(choices, { configured, engine: "pi", defaultEndpointId: "pi-zai-glm" })?.endpointId).toBe("pi-zai-glm");
    expect(resolveChatModelChoice(choices, { configured, engine: "pi", defaultEndpointId: "nope" })?.enabled).toBe(true);
  });

  it("lists ready Pi rows before disabled catalog rows on the legacy engine too", () => {
    const choices = buildChatModelChoices({ providers, configured, legacyModels: ["legacy-a"], engine: "legacy" });
    const withPi = choices.filter((c) => !c.key.startsWith("legacy:"));
    expect(withPi[0]?.enabled).toBe(true);
    expect(withPi[0]?.configured).toBe(true);
    const standalone = choices.find((c) => c.endpointId === "pi-zai-glm");
    expect(standalone?.enabled).toBe(true);
    expect(choices.findIndex((c) => c.endpointId === "pi-zai-glm")).toBeLessThan(
      choices.findIndex((c) => !c.enabled),
    );
  });
});

describe("resolveCatalogListState (B4: empty vs zero-match vs load-failure stay distinguishable)", () => {
  it("announces a catalog load failure as an error, regardless of query", () => {
    for (const query of ["", "zai", "anything"]) {
      const state = resolveCatalogListState({ catalogError: true, query, matchCount: 0 });
      expect(state.kind).toBe("error");
      expect(state.announce).toBe(true);
      expect(state.message).toContain("Model catalog failed to load");
    }
  });

  it("maps a zero-match query to the explicit no-results message", () => {
    const state = resolveCatalogListState({ catalogError: false, query: "zz-no-such-model", matchCount: 0 });
    expect(state.kind).toBe("no-match");
    expect(state.announce).toBe(false);
    expect(state.message).toBe("No models match that search.");
  });

  it("maps an empty catalog (no query) to an explicit empty state, never 'available'", () => {
    const state = resolveCatalogListState({ catalogError: false, query: "", matchCount: 0 });
    expect(state.kind).toBe("empty-catalog");
    expect(state.message).toContain("No models are configured yet");
    expect(state.message).not.toContain("available");
  });

  it("keeps non-empty match sets as plain option lists", () => {
    const state = resolveCatalogListState({ catalogError: false, query: "", matchCount: 3 });
    expect(state.kind).toBe("options");
    expect(state.message).toBeNull();
  });

  it("treats a whitespace-only query as an empty catalog, not a zero-match search", () => {
    const state = resolveCatalogListState({ catalogError: false, query: "   ", matchCount: 0 });
    expect(state.kind).toBe("empty-catalog");
  });
});
