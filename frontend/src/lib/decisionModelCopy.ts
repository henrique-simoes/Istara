// Shared wording for decision models and assurance modes: Settings, Project Settings, onboarding
// and Ensemble Health all explain the same contract the same way (CF-SPEC-1, Phase 7).

import type { AssuranceMode } from "@/lib/catalogTypes";

export const DECISION_MODEL_EXPLAINER = {
  title: "What is a decision model?",
  lead:
    "A decision model answers a closed question about one item, such as choosing one of a few options or giving a score, and returns a probability for every possible answer. It does not write text. Istara uses it to decide what deserves your attention first.",
  principles: [
    {
      title: "Closed answers, calibrated odds",
      body: "Every answer comes with probabilities that Istara checks against your own review decisions before it trusts them.",
    },
    {
      title: "Triage, never authority",
      body: "A decision model only reorders and flags items for review. It never accepts, rejects or promotes research evidence, and never counts as a coder.",
    },
    {
      title: "Your data, your boundary",
      body: "A local model keeps data on your hardware. A hosted model, such as TypeSafe Jev, receives a project's data only after that project opts in.",
    },
  ],
  trust:
    "Each project starts in shadow mode: the model's answers are recorded and compared with your decisions, but they change nothing. After 50 reviewed items, if its probabilities are well calibrated (ECE at most 0.05) and its agreement with you is substantial (kappa at least 0.60), it may start routing items to the top of your review queue. If it drifts, it goes back to shadow mode by itself.",
} as const;

export const FIRST_ACTIVATION_STEPS = [
  {
    title: "Choose where it runs",
    body: "Use TypeSafe Jev through its hosted API or through OpenRouter, OpenAI Decisions (public beta), or a /v1/systemone server on your own machine (llama.cpp with Kev, Laya or OpenJev).",
  },
  {
    title: "Add it here",
    body: "Give it a name, the server address and a pinned model version. A hosted model also needs an API key, which is stored in your Keychain or the server's secret store and never shown again.",
  },
  {
    title: "Check the connection",
    body: "Istara sends one fixed test question with no research data and shows which model answered.",
  },
  {
    title: "Turn it on per project",
    body: "In Project Settings, choose an assurance mode that includes decision models. A hosted model also needs that project's explicit cloud consent.",
  },
] as const;

export const ASSURANCE_MODE_COPY: Record<AssuranceMode, { title: string; body: string }> = {
  auto: {
    title: "Automatic",
    body: "Istara picks an LLM judge method from the models available, as it did before modes existed.",
  },
  llm_judges: {
    title: "LLM judges only",
    body: "One model reviewing itself (Self-MoA), two judges, or a panel of three or more. Rich comments, but judges that share a model share its blind spots.",
  },
  decision_models: {
    title: "Decision models only",
    body: "Fast, cheap closed-question checks with calibrated probabilities. No LLM judge is called.",
  },
  both: {
    title: "Both, side by side",
    body: "LLM judges and decision models both review. Their results are shown next to each other and never merged into one vote.",
  },
  none: {
    title: "No automated review",
    body: "Outputs are marked unvalidated and go straight to you. Human review is required in every mode.",
  },
};

export const LLM_METHOD_LABELS: Record<string, string> = {
  auto: "Let Istara choose",
  self_moa: "Self-MoA (one model, several samples)",
  dual_run: "Two judges",
  full_ensemble: "Panel of three or more judges",
  adversarial_review: "Adversarial review",
  debate_rounds: "Debate rounds",
};

export const TRUST_STATUS_COPY: Record<string, { label: string; body: string }> = {
  calibrating: {
    label: "Calibrating",
    body: "Collecting reviewed items before the first trust check.",
  },
  shadow: {
    label: "Shadow",
    body: "Recorded and measured, with no effect on your queue.",
  },
  trusted: {
    label: "Trusted",
    body: "Calibrated against your reviews; may reorder and flag items.",
  },
};

const ERROR_COPY: Record<string, string> = {
  decider_api_key_required: "A hosted decision model needs an API key.",
  decider_endpoint_exists: "A decision model with this name already exists.",
  decider_api_key_custody_failed: "The API key could not be stored securely. Nothing was saved.",
  decider_configuration_invalid: "The saved decision-model configuration is invalid. Ask an administrator to fix it.",
  hosted_decider_needs_egress_opt_in: "To use a hosted decision model, first allow this project to send data to it.",
  egress_opt_in_is_for_hosted_endpoints: "Local decision models need no cloud consent.",
  unknown_decider_endpoint: "That decision model is no longer configured.",
  mode_needs_a_decider: "Choose at least one decision model for this mode.",
  missing_api_key: "No API key is stored for this decision model.",
};

export function decisionModelErrorMessage(error: unknown, fallback: string): string {
  const message = error instanceof Error ? error.message : String(error || "");
  return ERROR_COPY[message] || message || fallback;
}

// Mirrors backend is_alias_model_id: moving aliases change behaviour without notice.
export function isAliasModelId(model: string): boolean {
  const name = model.trim().toLowerCase();
  return name === "latest" || ["-latest", "-preview", "-stable"].some((suffix) => name.endsWith(suffix));
}
