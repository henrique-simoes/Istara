"use client";

import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, CheckCircle2, X, Plus, Trash2, Rocket } from "lucide-react";
import { deployments as deploymentsApi } from "@/lib/api";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";
import type { ChannelInstance } from "@/lib/types";
import {
  DEFAULT_CONSENT_MESSAGE,
  INITIAL_DRAFT,
  buildDeploymentPayload,
  canLeaveStep,
  type DeploymentDraft,
  type WizardStep,
  WIZARD_STEPS,
} from "./deploymentDraft";

const DEPLOYMENT_TYPES = [
  { id: "interview", label: "Interview", description: "Structured conversational interviews with adaptive follow-ups" },
  { id: "survey", label: "Survey", description: "Sequential question delivery with fixed structure" },
  { id: "diary_study", label: "Diary Study", description: "Longitudinal check-ins over days or weeks" },
] as const;

const INPUT =
  "px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500";
const LABEL = "block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1";
const CHECKBOX = "rounded border-slate-300 dark:border-slate-600 text-istara-600 focus:ring-istara-500";

type Patch = (update: Partial<DeploymentDraft>) => void;

interface StepProps {
  draft: DeploymentDraft;
  patch: Patch;
}

function StepHeading({ title, lead }: { title: string; lead: string }) {
  return (
    <>
      <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">{title}</h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">{lead}</p>
    </>
  );
}

function TypeStep({ draft, patch }: StepProps) {
  return (
    <div>
      <StepHeading title="Deployment Type" lead="What kind of research do you want to deploy?" />
      <div className="space-y-3">
        {DEPLOYMENT_TYPES.map((t) => (
          <button
            key={t.id}
            onClick={() => patch({ deploymentType: t.id })}
            aria-pressed={draft.deploymentType === t.id}
            className={cn(
              "flex flex-col w-full p-4 rounded-xl border-2 transition-all text-left",
              draft.deploymentType === t.id
                ? "border-istara-500 bg-istara-50 dark:bg-istara-900/20"
                : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600"
            )}
          >
            <span className="text-sm font-medium text-slate-900 dark:text-white capitalize">{t.label}</span>
            <span className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function QuestionsStep({ draft, patch }: StepProps) {
  const { questions } = draft;
  const setText = (idx: number, text: string) =>
    patch({ questions: questions.map((q, i) => (i === idx ? { ...q, text } : q)) });
  return (
    <div>
      <StepHeading title="Define Questions" lead="Add the questions for your research deployment." />
      <div className="space-y-3">
        {questions.map((q, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className="text-xs font-medium text-slate-400 mt-2.5 w-6 shrink-0">Q{i + 1}</span>
            <input
              type="text"
              aria-label={`Question ${i + 1}`}
              placeholder={`Question ${i + 1}...`}
              value={q.text}
              onChange={(e) => setText(i, e.target.value)}
              className={cn("flex-1", INPUT)}
            />
            {questions.length > 1 && (
              <button
                onClick={() => patch({ questions: questions.filter((_, j) => j !== i) })}
                aria-label="Remove question"
                className="p-2 rounded-lg text-slate-400 hover:text-red-500 transition-colors"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>
        ))}
        <button
          onClick={() => patch({ questions: [...questions, { text: "", type: "open" }] })}
          className="flex items-center gap-1 text-sm text-istara-600 hover:text-istara-700 dark:text-istara-400 transition-colors"
        >
          <Plus size={14} /> Add Question
        </button>
      </div>
    </div>
  );
}

function ScreenerEditor({ draft, patch }: StepProps) {
  const { screener } = draft;
  const update = (idx: number, field: "text" | "accept", value: string) =>
    patch({ screener: screener.map((item, i) => (i === idx ? { ...item, [field]: value } : item)) });
  return (
    <div>
      <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Screening questions</p>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-2">
        Asked after consent. List the answers that qualify, separated by commas; leave empty to accept any answer.
      </p>
      <div className="space-y-2">
        {screener.map((item, i) => (
          <div key={i} className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              aria-label={`Screening question ${i + 1}`}
              placeholder="e.g., Do you export reports every week?"
              value={item.text}
              onChange={(e) => update(i, "text", e.target.value)}
              className={cn("flex-1 min-w-0", INPUT)}
            />
            <div className="flex gap-2">
              <input
                type="text"
                aria-label={`Qualifying answers for screening question ${i + 1}`}
                placeholder="yes"
                value={item.accept}
                onChange={(e) => update(i, "accept", e.target.value)}
                className={cn("w-full sm:w-32", INPUT)}
              />
              <button
                onClick={() => patch({ screener: screener.filter((_, j) => j !== i) })}
                aria-label={`Remove screening question ${i + 1}`}
                className="p-2 rounded-lg text-slate-400 hover:text-red-500 transition-colors"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
        <button
          onClick={() => patch({ screener: [...screener, { text: "", accept: "" }] })}
          className="flex items-center gap-1 text-sm text-istara-600 hover:text-istara-700 dark:text-istara-400 transition-colors"
        >
          <Plus size={14} /> Add screening question
        </button>
      </div>
    </div>
  );
}

function ParticipantsStep({ draft, patch }: StepProps) {
  return (
    <div>
      <StepHeading
        title="Consent & Screening"
        lead="What participants see first. Nothing they send is stored as research data until they agree and qualify."
      />
      <div className="space-y-4">
        <div>
          <label htmlFor="deployment-intro" className={LABEL}>
            Welcome message <span className="font-normal text-slate-400">(optional)</span>
          </label>
          <textarea
            id="deployment-intro"
            rows={2}
            value={draft.introMessage}
            onChange={(e) => patch({ introMessage: e.target.value })}
            placeholder="Hi! Thanks for helping us improve our product."
            className={cn("w-full", INPUT)}
          />
        </div>
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={draft.consentRequired}
            onChange={(e) => patch({ consentRequired: e.target.checked })}
            className={cn("mt-0.5", CHECKBOX)}
          />
          <div>
            <span className="text-sm font-medium text-slate-900 dark:text-white">Ask for informed consent</span>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Participants reply YES or NO. A NO ends the conversation and nothing is stored.
            </p>
          </div>
        </label>
        {draft.consentRequired ? (
          <div>
            <label htmlFor="deployment-consent" className={LABEL}>
              Consent statement
            </label>
            <textarea
              id="deployment-consent"
              rows={4}
              value={draft.consentMessage}
              onChange={(e) => patch({ consentMessage: e.target.value })}
              className={cn("w-full", INPUT)}
            />
          </div>
        ) : (
          <p role="note" className="text-xs rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
            Without a consent step, answers are stored from the first question. Make sure you have consent another way.
          </p>
        )}
        <ScreenerEditor draft={draft} patch={patch} />
      </div>
    </div>
  );
}

function AdaptiveStep({ draft, patch }: StepProps) {
  return (
    <div>
      <StepHeading title="Adaptive Configuration" lead="Configure how the AI adapts during conversations." />
      <div className="space-y-4">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={draft.adaptiveEnabled}
            onChange={(e) => patch({ adaptiveEnabled: e.target.checked })}
            className={CHECKBOX}
          />
          <div>
            <span className="text-sm font-medium text-slate-900 dark:text-white">Enable Adaptive Follow-ups</span>
            <p className="text-xs text-slate-500 dark:text-slate-400">AI will generate context-aware follow-up questions</p>
          </div>
        </label>
        {draft.adaptiveEnabled && (
          <div>
            <label htmlFor="deployment-max-follow-ups" className={LABEL}>
              Max Follow-ups per Question
            </label>
            <input
              id="deployment-max-follow-ups"
              type="number"
              min={0}
              max={5}
              value={draft.maxFollowUps}
              onChange={(e) => patch({ maxFollowUps: parseInt(e.target.value) || 0 })}
              className={cn("w-24", INPUT)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function ChannelsStep({ draft, patch, channels }: StepProps & { channels: ChannelInstance[] }) {
  const toggle = (id: string) =>
    patch({
      selectedChannels: draft.selectedChannels.includes(id)
        ? draft.selectedChannels.filter((c) => c !== id)
        : [...draft.selectedChannels, id],
    });
  return (
    <div>
      <StepHeading title="Select Channels" lead="Choose which messaging channels to deploy to." />
      {channels.length === 0 ? (
        <div className="text-center py-8 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
          <p className="text-sm text-slate-500 dark:text-slate-400">No active channels available.</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Add and activate channels from the Messaging tab first.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {channels.map((ch) => (
            <label
              key={ch.id}
              className={cn(
                "flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all",
                draft.selectedChannels.includes(ch.id)
                  ? "border-istara-500 bg-istara-50 dark:bg-istara-900/20"
                  : "border-slate-200 dark:border-slate-700"
              )}
            >
              <input
                type="checkbox"
                checked={draft.selectedChannels.includes(ch.id)}
                onChange={() => toggle(ch.id)}
                className={CHECKBOX}
              />
              <div>
                <span className="text-sm font-medium text-slate-900 dark:text-white">{ch.name}</span>
                <p className="text-xs text-slate-500 dark:text-slate-400 capitalize">{ch.platform.replace("_", " ")}</p>
              </div>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

function OptionalLabel({ htmlFor, children }: { htmlFor: string; children: string }) {
  return (
    <label htmlFor={htmlFor} className={LABEL}>
      {children} <span className="font-normal text-slate-400">(optional)</span>
    </label>
  );
}

function TargetsStep({ draft, patch }: StepProps) {
  return (
    <div>
      <StepHeading
        title="Targets & Wrap-up"
        lead="Name your deployment, set the number of participants, and decide how it ends."
      />
      <div className="space-y-4">
        <div>
          <label htmlFor="deployment-name" className={LABEL}>Deployment Name</label>
          <input
            id="deployment-name"
            type="text"
            placeholder="e.g., Q1 User Interview Sprint"
            value={draft.name}
            onChange={(e) => patch({ name: e.target.value })}
            className={cn("w-full", INPUT)}
            autoFocus
          />
        </div>
        <div>
          <label htmlFor="deployment-target" className={LABEL}>Target participants</label>
          <input
            id="deployment-target"
            type="number"
            min={1}
            value={draft.targetResponses}
            onChange={(e) => patch({ targetResponses: parseInt(e.target.value) || 1 })}
            className={cn("w-32", INPUT)}
          />
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            When this many participants have finished, new people are told the study is full.
            Anyone already taking part can finish.
          </p>
        </div>
        <div>
          <OptionalLabel htmlFor="deployment-closing">Closing question</OptionalLabel>
          <input
            id="deployment-closing"
            type="text"
            placeholder="e.g., Is there anything else you'd like to tell us?"
            value={draft.closingQuestion}
            onChange={(e) => patch({ closingQuestion: e.target.value })}
            className={cn("w-full", INPUT)}
          />
        </div>
        <div>
          <OptionalLabel htmlFor="deployment-thanks">Thank-you message</OptionalLabel>
          <input
            id="deployment-thanks"
            type="text"
            placeholder="Thank you for your time!"
            value={draft.thankYouMessage}
            onChange={(e) => patch({ thankYouMessage: e.target.value })}
            className={cn("w-full", INPUT)}
          />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={draft.remindersEnabled}
              onChange={(e) => patch({ remindersEnabled: e.target.checked })}
              className={CHECKBOX}
            />
            <span className="text-sm font-medium text-slate-900 dark:text-white">Send one reminder after</span>
          </label>
          <input
            type="number"
            min={1}
            aria-label="Reminder delay in hours"
            disabled={!draft.remindersEnabled}
            value={draft.reminderAfterHours}
            onChange={(e) => patch({ reminderAfterHours: Math.max(1, parseInt(e.target.value) || 1) })}
            className={cn("w-20 disabled:opacity-50", INPUT)}
          />
          <span className="text-sm text-slate-600 dark:text-slate-400">hours of silence</span>
        </div>
      </div>
    </div>
  );
}

function DeployStep({
  draft,
  deployed,
  deploying,
  deployError,
  onDeploy,
}: {
  draft: DeploymentDraft;
  deployed: boolean;
  deploying: boolean;
  deployError: string | null;
  onDeploy: () => void;
}) {
  if (deployed) {
    return (
      <div className="text-center py-4">
        <CheckCircle2 size={48} className="mx-auto mb-4 text-istara-500" />
        <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Deployment Created!</h2>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          &ldquo;{draft.name}&rdquo; is ready. Activate it from the deployments dashboard to begin collecting responses.
        </p>
      </div>
    );
  }
  const screeningCount = draft.screener.filter((item) => item.text.trim()).length;
  return (
    <div className="text-center py-4">
      <Rocket size={48} className="mx-auto mb-4 text-istara-500" />
      <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Ready to Deploy</h2>
      <div className="text-sm text-slate-600 dark:text-slate-400 text-left max-w-sm mx-auto space-y-1 mb-6">
        <p><strong>Type:</strong> {draft.deploymentType}</p>
        <p><strong>Questions:</strong> {draft.questions.filter((q) => q.text.trim()).length}</p>
        <p><strong>Channels:</strong> {draft.selectedChannels.length}</p>
        <p><strong>Target:</strong> {draft.targetResponses} participants</p>
        <p><strong>Consent:</strong> {draft.consentRequired ? "asked first" : "not asked"}</p>
        <p><strong>Screening questions:</strong> {screeningCount}</p>
        <p><strong>Reminder:</strong> {draft.remindersEnabled ? `after ${draft.reminderAfterHours} h` : "off"}</p>
      </div>
      {deployError && <p role="alert" className="mb-4 text-sm text-red-600 dark:text-red-400">{deployError}</p>}
      <button
        onClick={onDeploy}
        disabled={deploying}
        className="px-6 py-2.5 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50 transition-colors"
      >
        {deploying ? "Creating..." : "Create Deployment"}
      </button>
    </div>
  );
}

function StepDots({ stepIndex }: { stepIndex: number }) {
  return (
    <div className="flex items-center gap-2">
      {WIZARD_STEPS.map((_, i) => (
        <div
          key={i}
          className={cn(
            "w-2 h-2 rounded-full transition-colors",
            i === stepIndex ? "bg-istara-500" : i < stepIndex ? "bg-istara-300" : "bg-slate-200 dark:bg-slate-700"
          )}
        />
      ))}
    </div>
  );
}

interface DeploymentWizardProps {
  onClose: () => void;
}

export default function DeploymentWizard({ onClose }: DeploymentWizardProps) {
  const { channelInstances, fetchChannels } = useIntegrationsStore();
  const { activeProjectId } = useProjectStore();
  const [currentStep, setCurrentStep] = useState<WizardStep>("type");
  const [draft, setDraft] = useState<DeploymentDraft>({ ...INITIAL_DRAFT, consentMessage: DEFAULT_CONSENT_MESSAGE });
  const [deploying, setDeploying] = useState(false);
  const [deployed, setDeployed] = useState(false);
  const [deployError, setDeployError] = useState<string | null>(null);
  const patch: Patch = (update) => setDraft((prev) => ({ ...prev, ...update }));

  useEffect(() => {
    fetchChannels(undefined, activeProjectId);
  }, [activeProjectId, fetchChannels]);

  const stepIndex = WIZARD_STEPS.indexOf(currentStep);
  const goBack = () => { if (stepIndex > 0) setCurrentStep(WIZARD_STEPS[stepIndex - 1]); };
  const goNext = () => { if (stepIndex < WIZARD_STEPS.length - 1) setCurrentStep(WIZARD_STEPS[stepIndex + 1]); };

  const handleDeploy = async () => {
    if (!activeProjectId || !draft.deploymentType) return;
    setDeploying(true);
    setDeployError(null);
    try {
      await deploymentsApi.create(buildDeploymentPayload(draft, activeProjectId));
      setDeployed(true);
    } catch (err) {
      setDeployError(err instanceof Error ? err.message : "The deployment could not be created.");
    } finally {
      setDeploying(false);
    }
  };

  const activeChannels = activeProjectId
    ? channelInstances.filter((c) => c.is_active && c.project_id === activeProjectId)
    : [];

  const steps: Record<WizardStep, React.ReactNode> = {
    type: <TypeStep draft={draft} patch={patch} />,
    questions: <QuestionsStep draft={draft} patch={patch} />,
    participants: <ParticipantsStep draft={draft} patch={patch} />,
    adaptive: <AdaptiveStep draft={draft} patch={patch} />,
    channels: <ChannelsStep draft={draft} patch={patch} channels={activeChannels} />,
    targets: <TargetsStep draft={draft} patch={patch} />,
    deploy: (
      <DeployStep draft={draft} deployed={deployed} deploying={deploying} deployError={deployError} onDeploy={handleDeploy} />
    ),
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
      <section
        aria-label="New deployment wizard"
        className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 w-full max-w-2xl overflow-hidden"
      >
        <div className="h-1 bg-slate-100 dark:bg-slate-800">
          <div className="h-full bg-istara-500 transition-all duration-300" style={{ width: `${((stepIndex + 1) / WIZARD_STEPS.length) * 100}%` }} />
        </div>

        <div className="flex justify-end px-4 pt-3">
          <button onClick={onClose} aria-label="Close wizard" className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="p-6 pt-2 max-h-[70vh] overflow-y-auto">{steps[currentStep]}</div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-800">
          <div>
            {stepIndex > 0 && !deployed && (
              <button onClick={goBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors">
                <ChevronLeft size={14} /> Back
              </button>
            )}
          </div>
          <StepDots stepIndex={stepIndex} />
          <div>
            {deployed ? (
              <button onClick={onClose} className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors">Done</button>
            ) : currentStep === "deploy" ? null : (
              <button
                onClick={goNext}
                disabled={!canLeaveStep(currentStep, draft)}
                className="flex items-center gap-1 px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next <ChevronRight size={14} />
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
