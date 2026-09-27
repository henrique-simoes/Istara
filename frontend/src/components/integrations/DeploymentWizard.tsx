"use client";

import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, CheckCircle2, X, Plus, Trash2, Rocket } from "lucide-react";
import { deployments as deploymentsApi } from "@/lib/api";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";

const STEPS = ["type", "questions", "participants", "adaptive", "channels", "targets", "deploy"] as const;
type Step = (typeof STEPS)[number];

const DEPLOYMENT_TYPES = [
  { id: "interview", label: "Interview", description: "Structured conversational interviews with adaptive follow-ups" },
  { id: "survey", label: "Survey", description: "Sequential question delivery with fixed structure" },
  { id: "diary_study", label: "Diary Study", description: "Longitudinal check-ins over days or weeks" },
] as const;

const DEFAULT_CONSENT_MESSAGE =
  "Before we start: this is a research study. The research team will store and analyse your answers to improve the product, and may quote them in research reports without your name. Taking part is voluntary, and you can stop at any time by replying STOP.";

interface ScreenerDraft {
  text: string;
  accept: string;
}

interface DeploymentWizardProps {
  onClose: () => void;
}

export default function DeploymentWizard({ onClose }: DeploymentWizardProps) {
  const { channelInstances, fetchChannels } = useIntegrationsStore();
  const { activeProjectId } = useProjectStore();
  const [currentStep, setCurrentStep] = useState<Step>("type");
  const [deploymentType, setDeploymentType] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [questions, setQuestions] = useState<Array<{ text: string; type: string }>>([{ text: "", type: "open" }]);
  const [adaptiveEnabled, setAdaptiveEnabled] = useState(true);
  const [maxFollowUps, setMaxFollowUps] = useState(2);
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [targetResponses, setTargetResponses] = useState(20);
  const [introMessage, setIntroMessage] = useState("");
  const [consentRequired, setConsentRequired] = useState(true);
  const [consentMessage, setConsentMessage] = useState(DEFAULT_CONSENT_MESSAGE);
  const [screener, setScreener] = useState<ScreenerDraft[]>([]);
  const [closingQuestion, setClosingQuestion] = useState("");
  const [thankYouMessage, setThankYouMessage] = useState("");
  const [remindersEnabled, setRemindersEnabled] = useState(true);
  const [reminderAfterHours, setReminderAfterHours] = useState(24);
  const [deploying, setDeploying] = useState(false);
  const [deployed, setDeployed] = useState(false);
  const [deployError, setDeployError] = useState<string | null>(null);

  useEffect(() => {
    fetchChannels(undefined, activeProjectId);
  }, [activeProjectId, fetchChannels]);

  const stepIndex = STEPS.indexOf(currentStep);
  const goBack = () => { if (stepIndex > 0) setCurrentStep(STEPS[stepIndex - 1]); };
  const goNext = () => { if (stepIndex < STEPS.length - 1) setCurrentStep(STEPS[stepIndex + 1]); };

  const addQuestion = () => setQuestions([...questions, { text: "", type: "open" }]);
  const removeQuestion = (idx: number) => setQuestions(questions.filter((_, i) => i !== idx));
  const updateQuestion = (idx: number, text: string) => {
    const updated = [...questions];
    updated[idx] = { ...updated[idx], text };
    setQuestions(updated);
  };

  const updateScreener = (idx: number, field: keyof ScreenerDraft, value: string) => {
    setScreener((prev) => prev.map((item, i) => (i === idx ? { ...item, [field]: value } : item)));
  };

  const toggleChannel = (id: string) => {
    setSelectedChannels((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const handleDeploy = async () => {
    if (!activeProjectId || !deploymentType) return;
    setDeploying(true);
    setDeployError(null);
    try {
      const config: Record<string, unknown> = {
        adaptive_enabled: adaptiveEnabled,
        max_follow_ups: maxFollowUps,
        consent_required: consentRequired,
        consent_message: consentRequired ? consentMessage.trim() || DEFAULT_CONSENT_MESSAGE : "",
        screener: screener
          .filter((item) => item.text.trim())
          .map((item) => ({
            text: item.text.trim(),
            accept: item.accept.split(",").map((a) => a.trim()).filter(Boolean),
          })),
        reminder_after_hours: remindersEnabled ? reminderAfterHours : 0,
        max_reminders: remindersEnabled ? 1 : 0,
      };
      if (introMessage.trim()) config.intro_message = introMessage.trim();
      if (closingQuestion.trim()) config.closing_question = closingQuestion.trim();
      if (thankYouMessage.trim()) config.thank_you_message = thankYouMessage.trim();
      await deploymentsApi.create({
        project_id: activeProjectId,
        name: name || `${deploymentType} deployment`,
        deployment_type: deploymentType,
        questions: questions.filter((q) => q.text.trim()),
        config,
        channel_instance_ids: selectedChannels,
        target_responses: targetResponses,
      });
      setDeployed(true);
    } catch (err) {
      setDeployError(err instanceof Error ? err.message : "The deployment could not be created.");
    } finally {
      setDeploying(false);
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case "type": return !!deploymentType;
      case "questions": return questions.some((q) => q.text.trim());
      case "participants": return !consentRequired || consentMessage.trim().length > 0;
      case "adaptive": return true;
      case "channels": return selectedChannels.length > 0;
      case "targets": return targetResponses > 0 && name.trim().length > 0;
      default: return true;
    }
  };

  const activeChannels = activeProjectId
    ? channelInstances.filter((c) => c.is_active && c.project_id === activeProjectId)
    : [];

  return (
    <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
      <section
        aria-label="New deployment wizard"
        className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 w-full max-w-2xl overflow-hidden"
      >
        {/* Progress bar */}
        <div className="h-1 bg-slate-100 dark:bg-slate-800">
          <div className="h-full bg-istara-500 transition-all duration-300" style={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }} />
        </div>

        <div className="flex justify-end px-4 pt-3">
          <button onClick={onClose} aria-label="Close wizard" className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="p-6 pt-2 max-h-[70vh] overflow-y-auto">
          {/* Step: Type */}
          {currentStep === "type" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Deployment Type</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">What kind of research do you want to deploy?</p>
              <div className="space-y-3">
                {DEPLOYMENT_TYPES.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setDeploymentType(t.id)}
                    aria-pressed={deploymentType === t.id}
                    className={cn(
                      "flex flex-col w-full p-4 rounded-xl border-2 transition-all text-left",
                      deploymentType === t.id
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
          )}

          {/* Step: Questions */}
          {currentStep === "questions" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Define Questions</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">Add the questions for your research deployment.</p>
              <div className="space-y-3">
                {questions.map((q, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-xs font-medium text-slate-400 mt-2.5 w-6 shrink-0">Q{i + 1}</span>
                    <input
                      type="text"
                      aria-label={`Question ${i + 1}`}
                      placeholder={`Question ${i + 1}...`}
                      value={q.text}
                      onChange={(e) => updateQuestion(i, e.target.value)}
                      className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                    />
                    {questions.length > 1 && (
                      <button onClick={() => removeQuestion(i)} aria-label="Remove question" className="p-2 rounded-lg text-slate-400 hover:text-red-500 transition-colors">
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                ))}
                <button onClick={addQuestion} className="flex items-center gap-1 text-sm text-istara-600 hover:text-istara-700 dark:text-istara-400 transition-colors">
                  <Plus size={14} /> Add Question
                </button>
              </div>
            </div>
          )}

          {/* Step: Consent & screening */}
          {currentStep === "participants" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Consent &amp; Screening</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                What participants see first. Nothing they send is stored as research data until they agree and qualify.
              </p>
              <div className="space-y-4">
                <div>
                  <label htmlFor="deployment-intro" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Welcome message <span className="font-normal text-slate-400">(optional)</span>
                  </label>
                  <textarea
                    id="deployment-intro"
                    rows={2}
                    value={introMessage}
                    onChange={(e) => setIntroMessage(e.target.value)}
                    placeholder="Hi! Thanks for helping us improve our product."
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                  />
                </div>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={consentRequired}
                    onChange={(e) => setConsentRequired(e.target.checked)}
                    className="mt-0.5 rounded border-slate-300 dark:border-slate-600 text-istara-600 focus:ring-istara-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-slate-900 dark:text-white">Ask for informed consent</span>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Participants reply YES or NO. A NO ends the conversation and nothing is stored.
                    </p>
                  </div>
                </label>
                {consentRequired && (
                  <div>
                    <label htmlFor="deployment-consent" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Consent statement
                    </label>
                    <textarea
                      id="deployment-consent"
                      rows={4}
                      value={consentMessage}
                      onChange={(e) => setConsentMessage(e.target.value)}
                      className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                    />
                  </div>
                )}
                {!consentRequired && (
                  <p role="note" className="text-xs rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
                    Without a consent step, answers are stored from the first question. Make sure you have consent another way.
                  </p>
                )}
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
                          onChange={(e) => updateScreener(i, "text", e.target.value)}
                          className="flex-1 min-w-0 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                        />
                        <div className="flex gap-2">
                          <input
                            type="text"
                            aria-label={`Qualifying answers for screening question ${i + 1}`}
                            placeholder="yes"
                            value={item.accept}
                            onChange={(e) => updateScreener(i, "accept", e.target.value)}
                            className="w-full sm:w-32 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                          />
                          <button
                            onClick={() => setScreener((prev) => prev.filter((_, j) => j !== i))}
                            aria-label={`Remove screening question ${i + 1}`}
                            className="p-2 rounded-lg text-slate-400 hover:text-red-500 transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    ))}
                    <button
                      onClick={() => setScreener((prev) => [...prev, { text: "", accept: "" }])}
                      className="flex items-center gap-1 text-sm text-istara-600 hover:text-istara-700 dark:text-istara-400 transition-colors"
                    >
                      <Plus size={14} /> Add screening question
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step: Adaptive */}
          {currentStep === "adaptive" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Adaptive Configuration</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">Configure how the AI adapts during conversations.</p>
              <div className="space-y-4">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={adaptiveEnabled}
                    onChange={(e) => setAdaptiveEnabled(e.target.checked)}
                    className="rounded border-slate-300 dark:border-slate-600 text-istara-600 focus:ring-istara-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-slate-900 dark:text-white">Enable Adaptive Follow-ups</span>
                    <p className="text-xs text-slate-500 dark:text-slate-400">AI will generate context-aware follow-up questions</p>
                  </div>
                </label>
                {adaptiveEnabled && (
                  <div>
                    <label htmlFor="deployment-max-follow-ups" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Max Follow-ups per Question
                    </label>
                    <input
                      id="deployment-max-follow-ups"
                      type="number"
                      min={0}
                      max={5}
                      value={maxFollowUps}
                      onChange={(e) => setMaxFollowUps(parseInt(e.target.value) || 0)}
                      className="w-24 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step: Channels */}
          {currentStep === "channels" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Select Channels</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">Choose which messaging channels to deploy to.</p>
              {activeChannels.length === 0 ? (
                <div className="text-center py-8 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
                  <p className="text-sm text-slate-500 dark:text-slate-400">No active channels available.</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Add and activate channels from the Messaging tab first.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {activeChannels.map((ch) => (
                    <label
                      key={ch.id}
                      className={cn(
                        "flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all",
                        selectedChannels.includes(ch.id)
                          ? "border-istara-500 bg-istara-50 dark:bg-istara-900/20"
                          : "border-slate-200 dark:border-slate-700"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={selectedChannels.includes(ch.id)}
                        onChange={() => toggleChannel(ch.id)}
                        className="rounded border-slate-300 dark:border-slate-600 text-istara-600 focus:ring-istara-500"
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
          )}

          {/* Step: Targets */}
          {currentStep === "targets" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Targets &amp; Wrap-up</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">Name your deployment, set the number of participants, and decide how it ends.</p>
              <div className="space-y-4">
                <div>
                  <label htmlFor="deployment-name" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Deployment Name</label>
                  <input
                    id="deployment-name"
                    type="text"
                    placeholder="e.g., Q1 User Interview Sprint"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                    autoFocus
                  />
                </div>
                <div>
                  <label htmlFor="deployment-target" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Target participants</label>
                  <input
                    id="deployment-target"
                    type="number"
                    min={1}
                    value={targetResponses}
                    onChange={(e) => setTargetResponses(parseInt(e.target.value) || 1)}
                    className="w-32 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                  />
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    When this many participants have finished, new people are told the study is full.
                    Anyone already taking part can finish.
                  </p>
                </div>
                <div>
                  <label htmlFor="deployment-closing" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Closing question <span className="font-normal text-slate-400">(optional)</span>
                  </label>
                  <input
                    id="deployment-closing"
                    type="text"
                    placeholder="e.g., Is there anything else you'd like to tell us?"
                    value={closingQuestion}
                    onChange={(e) => setClosingQuestion(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                  />
                </div>
                <div>
                  <label htmlFor="deployment-thanks" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Thank-you message <span className="font-normal text-slate-400">(optional)</span>
                  </label>
                  <input
                    id="deployment-thanks"
                    type="text"
                    placeholder="Thank you for your time!"
                    value={thankYouMessage}
                    onChange={(e) => setThankYouMessage(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                  />
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={remindersEnabled}
                      onChange={(e) => setRemindersEnabled(e.target.checked)}
                      className="rounded border-slate-300 dark:border-slate-600 text-istara-600 focus:ring-istara-500"
                    />
                    <span className="text-sm font-medium text-slate-900 dark:text-white">Send one reminder after</span>
                  </label>
                  <input
                    type="number"
                    min={1}
                    aria-label="Reminder delay in hours"
                    disabled={!remindersEnabled}
                    value={reminderAfterHours}
                    onChange={(e) => setReminderAfterHours(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-20 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500 disabled:opacity-50"
                  />
                  <span className="text-sm text-slate-600 dark:text-slate-400">hours of silence</span>
                </div>
              </div>
            </div>
          )}

          {/* Step: Deploy */}
          {currentStep === "deploy" && (
            <div className="text-center py-4">
              {deployed ? (
                <>
                  <CheckCircle2 size={48} className="mx-auto mb-4 text-istara-500" />
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Deployment Created!</h2>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    &ldquo;{name}&rdquo; is ready. Activate it from the deployments dashboard to begin collecting responses.
                  </p>
                </>
              ) : (
                <>
                  <Rocket size={48} className="mx-auto mb-4 text-istara-500" />
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Ready to Deploy</h2>
                  <div className="text-sm text-slate-600 dark:text-slate-400 text-left max-w-sm mx-auto space-y-1 mb-6">
                    <p><strong>Type:</strong> {deploymentType}</p>
                    <p><strong>Questions:</strong> {questions.filter((q) => q.text.trim()).length}</p>
                    <p><strong>Channels:</strong> {selectedChannels.length}</p>
                    <p><strong>Target:</strong> {targetResponses} participants</p>
                    <p><strong>Consent:</strong> {consentRequired ? "asked first" : "not asked"}</p>
                    <p><strong>Screening questions:</strong> {screener.filter((item) => item.text.trim()).length}</p>
                    <p><strong>Reminder:</strong> {remindersEnabled ? `after ${reminderAfterHours} h` : "off"}</p>
                  </div>
                  {deployError && (
                    <p role="alert" className="mb-4 text-sm text-red-600 dark:text-red-400">{deployError}</p>
                  )}
                  <button
                    onClick={handleDeploy}
                    disabled={deploying}
                    className="px-6 py-2.5 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50 transition-colors"
                  >
                    {deploying ? "Creating..." : "Create Deployment"}
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-800">
          <div>
            {stepIndex > 0 && !deployed && (
              <button onClick={goBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors">
                <ChevronLeft size={14} /> Back
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            {STEPS.map((_, i) => (
              <div key={i} className={cn("w-2 h-2 rounded-full transition-colors", i === stepIndex ? "bg-istara-500" : i < stepIndex ? "bg-istara-300" : "bg-slate-200 dark:bg-slate-700")} />
            ))}
          </div>
          <div>
            {deployed ? (
              <button onClick={onClose} className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors">Done</button>
            ) : currentStep === "deploy" ? null : (
              <button onClick={goNext} disabled={!canProceed()} className="flex items-center gap-1 px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                Next <ChevronRight size={14} />
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
