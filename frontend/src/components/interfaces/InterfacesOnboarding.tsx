"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Palette, ExternalLink, AlertTriangle, CheckCircle2, Sparkles } from "lucide-react";
import { interfaces as interfacesApi } from "@/lib/api";
import { useInterfacesStore } from "@/stores/interfacesStore";
import { cn } from "@/lib/utils";

const STEPS = ["welcome", "stitch", "figma", "privacy", "done"] as const;
type Step = typeof STEPS[number];

export default function InterfacesOnboarding() {
  const { dismissOnboarding, acknowledgePrivacy } = useInterfacesStore();
  const [currentStep, setCurrentStep] = useState<Step>("welcome");
  const [stitchKey, setStitchKey] = useState("");
  const [figmaToken, setFigmaToken] = useState("");
  const [savingStitch, setSavingStitch] = useState(false);
  const [savingFigma, setSavingFigma] = useState(false);
  const [stitchSaved, setStitchSaved] = useState(false);
  const [figmaSaved, setFigmaSaved] = useState(false);
  const [stitchError, setStitchError] = useState<string | null>(null);
  const [figmaError, setFigmaError] = useState<string | null>(null);
  const [privacyChecked, setPrivacyChecked] = useState(false);

  const stepIndex = STEPS.indexOf(currentStep);

  const goBack = () => {
    if (stepIndex > 0) setCurrentStep(STEPS[stepIndex - 1]);
  };
  const goNext = () => {
    if (stepIndex < STEPS.length - 1) setCurrentStep(STEPS[stepIndex + 1]);
  };

  const handleSaveStitch = async () => {
    if (!stitchKey.trim()) return;
    setSavingStitch(true);
    setStitchError(null);
    try {
      await interfacesApi.configure.stitch({ api_key: stitchKey.trim() });
      setStitchSaved(true);
    } catch (e: any) {
      setStitchError(e.message);
    } finally {
      setSavingStitch(false);
    }
  };

  const handleSaveFigma = async () => {
    if (!figmaToken.trim()) return;
    setSavingFigma(true);
    setFigmaError(null);
    try {
      await interfacesApi.configure.figma({ api_token: figmaToken.trim() });
      setFigmaSaved(true);
    } catch (e: any) {
      setFigmaError(e.message);
    } finally {
      setSavingFigma(false);
    }
  };

  const handleDone = () => {
    if (privacyChecked) acknowledgePrivacy();
    dismissOnboarding();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Progress bar */}
        <div className="h-1 bg-slate-100 dark:bg-slate-800">
          <div
            className="h-full bg-reclaw-500 transition-all duration-300"
            style={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }}
          />
        </div>

        <div className="p-6">
          {/* Welcome */}
          {currentStep === "welcome" && (
            <div className="text-center py-4">
              <Palette size={48} className="mx-auto mb-4 text-reclaw-500" />
              <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                Welcome to Interfaces
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-400 max-w-sm mx-auto">
                Interfaces bridges your research findings with actual design. Generate screens,
                import from Figma, and hand off specs to developers -- all informed by your UX research.
              </p>
            </div>
          )}

          {/* Stitch Setup */}
          {currentStep === "stitch" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">
                Stitch Setup (Google Gemini)
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                Stitch uses Google Gemini to generate screen designs from your prompts.
              </p>

              <div className="space-y-3">
                <input
                  type="password"
                  value={stitchKey}
                  onChange={(e) => setStitchKey(e.target.value)}
                  placeholder="Google Gemini API key"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                />

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleSaveStitch}
                    disabled={!stitchKey.trim() || savingStitch}
                    className="px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 transition-colors"
                  >
                    {savingStitch ? "Saving..." : "Save Key"}
                  </button>
                  {stitchSaved && (
                    <span className="flex items-center gap-1 text-sm text-green-600">
                      <CheckCircle2 size={14} /> Saved
                    </span>
                  )}
                </div>

                {stitchError && (
                  <p className="text-sm text-red-600 dark:text-red-400">{stitchError}</p>
                )}

                <a
                  href="https://aistudio.google.com/apikey"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-reclaw-600 hover:text-reclaw-700 dark:text-reclaw-400"
                >
                  <ExternalLink size={12} /> Get your API key
                </a>
              </div>
            </div>
          )}

          {/* Figma Setup */}
          {currentStep === "figma" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">
                Figma Setup
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                Connect Figma to import existing designs and extract design systems.
              </p>

              <div className="space-y-3">
                <input
                  type="password"
                  value={figmaToken}
                  onChange={(e) => setFigmaToken(e.target.value)}
                  placeholder="Figma personal access token"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                />

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleSaveFigma}
                    disabled={!figmaToken.trim() || savingFigma}
                    className="px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 transition-colors"
                  >
                    {savingFigma ? "Saving..." : "Save Token"}
                  </button>
                  {figmaSaved && (
                    <span className="flex items-center gap-1 text-sm text-green-600">
                      <CheckCircle2 size={14} /> Saved
                    </span>
                  )}
                </div>

                {figmaError && (
                  <p className="text-sm text-red-600 dark:text-red-400">{figmaError}</p>
                )}

                <a
                  href="https://www.figma.com/developers/api#access-tokens"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-reclaw-600 hover:text-reclaw-700 dark:text-reclaw-400"
                >
                  <ExternalLink size={12} /> Get your token
                </a>
              </div>
            </div>
          )}

          {/* Privacy */}
          {currentStep === "privacy" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-3">
                Privacy Notice
              </h2>

              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="text-amber-500 shrink-0 mt-0.5" size={20} />
                  <div>
                    <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-1">
                      Important: External Data Sharing
                    </p>
                    <p className="text-sm text-amber-700 dark:text-amber-300">
                      Sending data to Stitch or Figma breaks ReClaw&apos;s local-first approach.
                      Your research data and prompts will be shared with external services (Google/Figma).
                    </p>
                  </div>
                </div>
              </div>

              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={privacyChecked}
                  onChange={(e) => setPrivacyChecked(e.target.checked)}
                  className="mt-1 rounded border-slate-300 dark:border-slate-600 text-reclaw-600 focus:ring-reclaw-500"
                />
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  I understand that using Interfaces features will send data to external services,
                  and I acknowledge this breaks the local-first privacy model.
                </span>
              </label>
            </div>
          )}

          {/* Done */}
          {currentStep === "done" && (
            <div className="text-center py-4">
              <Sparkles size={48} className="mx-auto mb-4 text-reclaw-500" />
              <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                You&apos;re all set!
              </h2>
              <div className="text-sm text-slate-600 dark:text-slate-400 text-left max-w-sm mx-auto space-y-2 mt-4">
                <p><strong>Design Chat</strong> -- Discuss design decisions with the AI design lead</p>
                <p><strong>Generate</strong> -- Create screen designs from research findings</p>
                <p><strong>Screens</strong> -- Browse and manage generated screens</p>
                <p><strong>Figma</strong> -- Import designs and extract design systems</p>
                <p><strong>Handoff</strong> -- Generate design briefs and dev specs</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-800">
          <div>
            {stepIndex > 0 && currentStep !== "done" && (
              <button
                onClick={goBack}
                className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
              >
                <ChevronLeft size={14} /> Back
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Step indicators */}
            {STEPS.map((_, i) => (
              <div
                key={i}
                className={cn(
                  "w-2 h-2 rounded-full transition-colors",
                  i === stepIndex ? "bg-reclaw-500" : i < stepIndex ? "bg-reclaw-300" : "bg-slate-200 dark:bg-slate-700"
                )}
              />
            ))}
          </div>

          <div>
            {currentStep === "done" ? (
              <button
                onClick={handleDone}
                className="px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 transition-colors"
              >
                Get Started
              </button>
            ) : currentStep === "stitch" || currentStep === "figma" ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={goNext}
                  className="text-sm text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                >
                  Skip
                </button>
                <button
                  onClick={goNext}
                  className="flex items-center gap-1 px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 transition-colors"
                >
                  Next <ChevronRight size={14} />
                </button>
              </div>
            ) : currentStep === "privacy" ? (
              <button
                onClick={goNext}
                disabled={!privacyChecked}
                className="flex items-center gap-1 px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next <ChevronRight size={14} />
              </button>
            ) : (
              <button
                onClick={goNext}
                className="flex items-center gap-1 px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 transition-colors"
              >
                Next <ChevronRight size={14} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
