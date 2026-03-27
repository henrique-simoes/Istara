"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, CheckCircle2, AlertCircle, X, ClipboardList, FormInput, FileType } from "lucide-react";
import { surveys as surveysApi } from "@/lib/api";
import { cn } from "@/lib/utils";

const STEPS = ["platform", "credentials", "test", "done"] as const;
type Step = (typeof STEPS)[number];

const PLATFORMS = [
  { id: "surveymonkey", label: "SurveyMonkey", color: "#00BF6F", icon: ClipboardList, description: "Import surveys and responses" },
  { id: "google_forms", label: "Google Forms", color: "#673AB7", icon: FormInput, description: "Connect via Google API" },
  { id: "typeform", label: "Typeform", color: "#262627", icon: FileType, description: "Import typeforms and results" },
] as const;

const CREDENTIAL_FIELDS: Record<string, { label: string; placeholder: string; type: string }[]> = {
  surveymonkey: [{ label: "Access Token", placeholder: "SurveyMonkey access token", type: "password" }],
  google_forms: [{ label: "Service Account JSON", placeholder: "Paste Google service account JSON", type: "password" }],
  typeform: [{ label: "Personal Access Token", placeholder: "Typeform personal access token", type: "password" }],
};

interface SurveySetupWizardProps {
  onClose: () => void;
}

export default function SurveySetupWizard({ onClose }: SurveySetupWizardProps) {
  const [currentStep, setCurrentStep] = useState<Step>("platform");
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"success" | "error" | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const stepIndex = STEPS.indexOf(currentStep);
  const goBack = () => { if (stepIndex > 0) setCurrentStep(STEPS[stepIndex - 1]); };
  const goNext = () => { if (stepIndex < STEPS.length - 1) setCurrentStep(STEPS[stepIndex + 1]); };

  const handleTest = async () => {
    if (!selectedPlatform) return;
    setTesting(true);
    setTestResult(null);
    setTestError(null);
    try {
      await surveysApi.integrations.create({
        platform: selectedPlatform,
        name: `${PLATFORMS.find((p) => p.id === selectedPlatform)?.label} Integration`,
        config: credentials,
      });
      setTestResult("success");
      goNext();
    } catch (e: any) {
      setTestError(e.message);
      setTestResult("error");
    } finally {
      setTesting(false);
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case "platform": return !!selectedPlatform;
      case "credentials": return Object.values(credentials).some((v) => v.trim());
      case "test": return testResult === "success";
      default: return true;
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 w-full max-w-lg overflow-hidden">
        {/* Progress bar */}
        <div className="h-1 bg-slate-100 dark:bg-slate-800">
          <div className="h-full bg-reclaw-500 transition-all duration-300" style={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }} />
        </div>

        <div className="flex justify-end px-4 pt-3">
          <button onClick={onClose} aria-label="Close wizard" className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="p-6 pt-2">
          {/* Platform */}
          {currentStep === "platform" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Select Survey Platform</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">Choose which platform to connect.</p>
              <div className="space-y-3">
                {PLATFORMS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedPlatform(p.id)}
                    className={cn(
                      "flex items-center gap-3 w-full p-4 rounded-xl border-2 transition-all text-left",
                      selectedPlatform === p.id
                        ? "border-reclaw-500 bg-reclaw-50 dark:bg-reclaw-900/20"
                        : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600"
                    )}
                  >
                    <p.icon size={24} style={{ color: p.color }} />
                    <div>
                      <span className="text-sm font-medium text-slate-900 dark:text-white">{p.label}</span>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{p.description}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Credentials */}
          {currentStep === "credentials" && selectedPlatform && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Enter Credentials</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                Provide your {PLATFORMS.find((p) => p.id === selectedPlatform)?.label} API credentials.
              </p>
              <div className="space-y-3">
                {(CREDENTIAL_FIELDS[selectedPlatform] || []).map((field, i) => (
                  <div key={i}>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{field.label}</label>
                    <input
                      type={field.type}
                      placeholder={field.placeholder}
                      value={credentials[field.label] || ""}
                      onChange={(e) => setCredentials({ ...credentials, [field.label]: e.target.value })}
                      className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Test */}
          {currentStep === "test" && (
            <div className="text-center py-4">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Test Connection</h2>
              {testResult === "success" ? (
                <div className="space-y-3">
                  <CheckCircle2 size={48} className="mx-auto text-green-500" />
                  <p className="text-sm text-green-600 dark:text-green-400 font-medium">Connected successfully!</p>
                </div>
              ) : testResult === "error" ? (
                <div className="space-y-3">
                  <AlertCircle size={48} className="mx-auto text-red-500" />
                  <p className="text-sm text-red-600 dark:text-red-400">{testError || "Connection failed"}</p>
                  <button onClick={handleTest} disabled={testing} className="px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 transition-colors">
                    {testing ? "Testing..." : "Retry"}
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <button onClick={handleTest} disabled={testing} className="px-6 py-2.5 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 transition-colors">
                    {testing ? "Connecting..." : "Test Connection"}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Done */}
          {currentStep === "done" && (
            <div className="text-center py-4">
              <CheckCircle2 size={48} className="mx-auto mb-4 text-reclaw-500" />
              <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Platform Connected!</h2>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Your {PLATFORMS.find((p) => p.id === selectedPlatform)?.label} integration is ready.
                Surveys and responses will sync automatically.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-800">
          <div>
            {stepIndex > 0 && currentStep !== "done" && (
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
            {currentStep === "done" ? (
              <button onClick={onClose} className="px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 transition-colors">Done</button>
            ) : currentStep === "test" ? null : (
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
