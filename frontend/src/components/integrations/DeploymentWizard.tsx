"use client";

import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, CheckCircle2, X, Plus, Trash2, Rocket } from "lucide-react";
import { deployments as deploymentsApi } from "@/lib/api";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { cn } from "@/lib/utils";

const STEPS = ["type", "questions", "adaptive", "channels", "targets", "deploy"] as const;
type Step = (typeof STEPS)[number];

const DEPLOYMENT_TYPES = [
  { id: "interview", label: "Interview", description: "Structured conversational interviews with adaptive follow-ups" },
  { id: "survey", label: "Survey", description: "Sequential question delivery with fixed structure" },
  { id: "diary_study", label: "Diary Study", description: "Longitudinal check-ins over days or weeks" },
] as const;

interface DeploymentWizardProps {
  onClose: () => void;
}

export default function DeploymentWizard({ onClose }: DeploymentWizardProps) {
  const { channelInstances, fetchChannels } = useIntegrationsStore();
  const [currentStep, setCurrentStep] = useState<Step>("type");
  const [deploymentType, setDeploymentType] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [questions, setQuestions] = useState<Array<{ text: string; type: string }>>([{ text: "", type: "open" }]);
  const [adaptiveEnabled, setAdaptiveEnabled] = useState(true);
  const [maxFollowUps, setMaxFollowUps] = useState(2);
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [targetResponses, setTargetResponses] = useState(20);
  const [deploying, setDeploying] = useState(false);
  const [deployed, setDeployed] = useState(false);

  useEffect(() => {
    fetchChannels();
  }, [fetchChannels]);

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

  const toggleChannel = (id: string) => {
    setSelectedChannels((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const handleDeploy = async () => {
    setDeploying(true);
    try {
      await deploymentsApi.create({
        name: name || `${deploymentType} deployment`,
        deployment_type: deploymentType,
        questions: questions.filter((q) => q.text.trim()),
        config: { adaptive_enabled: adaptiveEnabled, max_follow_ups: maxFollowUps },
        channel_instance_ids: selectedChannels,
        target_responses: targetResponses,
      });
      setDeployed(true);
    } catch {
      // error
    } finally {
      setDeploying(false);
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case "type": return !!deploymentType;
      case "questions": return questions.some((q) => q.text.trim());
      case "adaptive": return true;
      case "channels": return selectedChannels.length > 0;
      case "targets": return targetResponses > 0 && name.trim().length > 0;
      default: return true;
    }
  };

  const activeChannels = channelInstances.filter((c) => c.is_active);

  return (
    <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 w-full max-w-2xl overflow-hidden">
        {/* Progress bar */}
        <div className="h-1 bg-slate-100 dark:bg-slate-800">
          <div className="h-full bg-reclaw-500 transition-all duration-300" style={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }} />
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
                    className={cn(
                      "flex flex-col w-full p-4 rounded-xl border-2 transition-all text-left",
                      deploymentType === t.id
                        ? "border-reclaw-500 bg-reclaw-50 dark:bg-reclaw-900/20"
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
                      placeholder={`Question ${i + 1}...`}
                      value={q.text}
                      onChange={(e) => updateQuestion(i, e.target.value)}
                      className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                    />
                    {questions.length > 1 && (
                      <button onClick={() => removeQuestion(i)} aria-label="Remove question" className="p-2 rounded-lg text-slate-400 hover:text-red-500 transition-colors">
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                ))}
                <button onClick={addQuestion} className="flex items-center gap-1 text-sm text-reclaw-600 hover:text-reclaw-700 dark:text-reclaw-400 transition-colors">
                  <Plus size={14} /> Add Question
                </button>
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
                    className="rounded border-slate-300 dark:border-slate-600 text-reclaw-600 focus:ring-reclaw-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-slate-900 dark:text-white">Enable Adaptive Follow-ups</span>
                    <p className="text-xs text-slate-500 dark:text-slate-400">AI will generate context-aware follow-up questions</p>
                  </div>
                </label>
                {adaptiveEnabled && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Max Follow-ups per Question
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={5}
                      value={maxFollowUps}
                      onChange={(e) => setMaxFollowUps(parseInt(e.target.value) || 0)}
                      className="w-24 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
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
                          ? "border-reclaw-500 bg-reclaw-50 dark:bg-reclaw-900/20"
                          : "border-slate-200 dark:border-slate-700"
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={selectedChannels.includes(ch.id)}
                        onChange={() => toggleChannel(ch.id)}
                        className="rounded border-slate-300 dark:border-slate-600 text-reclaw-600 focus:ring-reclaw-500"
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
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Set Targets</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">Name your deployment and set response targets.</p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Deployment Name</label>
                  <input
                    type="text"
                    placeholder="e.g., Q1 User Interview Sprint"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Target Responses</label>
                  <input
                    type="number"
                    min={1}
                    value={targetResponses}
                    onChange={(e) => setTargetResponses(parseInt(e.target.value) || 1)}
                    className="w-32 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                  />
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                    The deployment will auto-complete when this target is reached.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Step: Deploy */}
          {currentStep === "deploy" && (
            <div className="text-center py-4">
              {deployed ? (
                <>
                  <CheckCircle2 size={48} className="mx-auto mb-4 text-reclaw-500" />
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Deployment Created!</h2>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    &ldquo;{name}&rdquo; is ready. Activate it from the deployments dashboard to begin collecting responses.
                  </p>
                </>
              ) : (
                <>
                  <Rocket size={48} className="mx-auto mb-4 text-reclaw-500" />
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Ready to Deploy</h2>
                  <div className="text-sm text-slate-600 dark:text-slate-400 text-left max-w-sm mx-auto space-y-1 mb-6">
                    <p><strong>Type:</strong> {deploymentType}</p>
                    <p><strong>Questions:</strong> {questions.filter((q) => q.text.trim()).length}</p>
                    <p><strong>Channels:</strong> {selectedChannels.length}</p>
                    <p><strong>Target:</strong> {targetResponses} responses</p>
                  </div>
                  <button
                    onClick={handleDeploy}
                    disabled={deploying}
                    className="px-6 py-2.5 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 transition-colors"
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
              <div key={i} className={cn("w-2 h-2 rounded-full transition-colors", i === stepIndex ? "bg-reclaw-500" : i < stepIndex ? "bg-reclaw-300" : "bg-slate-200 dark:bg-slate-700")} />
            ))}
          </div>
          <div>
            {deployed ? (
              <button onClick={onClose} className="px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 transition-colors">Done</button>
            ) : currentStep === "deploy" ? null : (
              <button onClick={goNext} disabled={!canProceed()} className="flex items-center gap-1 px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                Next <ChevronRight size={14} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
