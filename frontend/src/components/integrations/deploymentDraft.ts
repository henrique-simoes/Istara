/** The research-deployment wizard's draft, its step rules, and the payload the API receives. */

export const WIZARD_STEPS = ["type", "questions", "participants", "adaptive", "channels", "targets", "deploy"] as const;
export type WizardStep = (typeof WIZARD_STEPS)[number];

export const DEFAULT_CONSENT_MESSAGE =
  "Before we start: this is a research study. The research team will store and analyse your answers to improve the product, and may quote them in research reports without your name. Taking part is voluntary, and you can stop at any time by replying STOP.";

export interface ScreenerDraft {
  text: string;
  accept: string;
}

export interface DeploymentDraft {
  deploymentType: string | null;
  name: string;
  questions: Array<{ text: string; type: string }>;
  introMessage: string;
  consentRequired: boolean;
  consentMessage: string;
  screener: ScreenerDraft[];
  adaptiveEnabled: boolean;
  maxFollowUps: number;
  selectedChannels: string[];
  targetResponses: number;
  closingQuestion: string;
  thankYouMessage: string;
  remindersEnabled: boolean;
  reminderAfterHours: number;
}

export const INITIAL_DRAFT: DeploymentDraft = {
  deploymentType: null,
  name: "",
  questions: [{ text: "", type: "open" }],
  introMessage: "",
  consentRequired: true,
  consentMessage: DEFAULT_CONSENT_MESSAGE,
  screener: [],
  adaptiveEnabled: true,
  maxFollowUps: 2,
  selectedChannels: [],
  targetResponses: 20,
  closingQuestion: "",
  thankYouMessage: "",
  remindersEnabled: true,
  reminderAfterHours: 24,
};

export function canLeaveStep(step: WizardStep, draft: DeploymentDraft): boolean {
  switch (step) {
    case "type":
      return !!draft.deploymentType;
    case "questions":
      return draft.questions.some((q) => q.text.trim());
    case "participants":
      return !draft.consentRequired || draft.consentMessage.trim().length > 0;
    case "channels":
      return draft.selectedChannels.length > 0;
    case "targets":
      return draft.targetResponses > 0 && draft.name.trim().length > 0;
    default:
      return true;
  }
}

/** The body for POST /api/deployments. Optional messages are sent only when written. */
export function buildDeploymentPayload(draft: DeploymentDraft, projectId: string) {
  const config: Record<string, unknown> = {
    adaptive_enabled: draft.adaptiveEnabled,
    max_follow_ups: draft.maxFollowUps,
    consent_required: draft.consentRequired,
    consent_message: draft.consentRequired ? draft.consentMessage.trim() || DEFAULT_CONSENT_MESSAGE : "",
    screener: draft.screener
      .filter((item) => item.text.trim())
      .map((item) => ({
        text: item.text.trim(),
        accept: item.accept.split(",").map((a) => a.trim()).filter(Boolean),
      })),
    reminder_after_hours: draft.remindersEnabled ? draft.reminderAfterHours : 0,
    max_reminders: draft.remindersEnabled ? 1 : 0,
  };
  if (draft.introMessage.trim()) config.intro_message = draft.introMessage.trim();
  if (draft.closingQuestion.trim()) config.closing_question = draft.closingQuestion.trim();
  if (draft.thankYouMessage.trim()) config.thank_you_message = draft.thankYouMessage.trim();
  return {
    project_id: projectId,
    name: draft.name || `${draft.deploymentType} deployment`,
    deployment_type: draft.deploymentType,
    questions: draft.questions.filter((q) => q.text.trim()),
    config,
    channel_instance_ids: draft.selectedChannels,
    target_responses: draft.targetResponses,
  };
}
