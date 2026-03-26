"use client";

import { useState } from "react";
import { Wand2, Loader2, Sparkles, X } from "lucide-react";
import { interfaces as interfacesApi } from "@/lib/api";
import { useInterfacesStore } from "@/stores/interfacesStore";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";
import PrivacyWarningBanner from "./PrivacyWarningBanner";
import FindingsPicker from "./FindingsPicker";
import ScreenPreview from "./ScreenPreview";

const DEVICE_TYPES = [
  { value: "MOBILE", label: "Mobile" },
  { value: "DESKTOP", label: "Desktop" },
  { value: "TABLET", label: "Tablet" },
  { value: "AGNOSTIC", label: "Agnostic" },
];

const MODELS = [
  { value: "GEMINI_3_FLASH", label: "Gemini 3 Flash" },
  { value: "GEMINI_3_PRO", label: "Gemini 3 Pro" },
];

export default function GenerateTab() {
  const { status, privacyAcknowledged, acknowledgePrivacy } = useInterfacesStore();
  const { activeProjectId } = useProjectStore();
  const [prompt, setPrompt] = useState("");
  const [deviceType, setDeviceType] = useState("MOBILE");
  const [model, setModel] = useState("GEMINI_3_FLASH");
  const [seedFindings, setSeedFindings] = useState<string[]>([]);
  const [showFindingsPicker, setShowFindingsPicker] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const stitchConfigured = status?.stitch_configured;

  const handleGenerate = async () => {
    if (!prompt.trim() || !activeProjectId || generating) return;
    setGenerating(true);
    setError(null);
    setResult(null);
    try {
      const data = await interfacesApi.generate({
        project_id: activeProjectId,
        prompt: prompt.trim(),
        device_type: deviceType,
        model,
        seed_finding_ids: seedFindings.length > 0 ? seedFindings : undefined,
      });
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  if (!stitchConfigured) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <Wand2 size={40} className="mx-auto mb-4 text-slate-300 dark:text-slate-600" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">Stitch Not Configured</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
            Screen generation requires Stitch (Google Gemini) to be configured. Set up your API key in the onboarding wizard or Figma tab settings.
          </p>
          <button
            onClick={() => useInterfacesStore.getState().setActiveTab("figma")}
            className="px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 transition-colors"
          >
            Configure Stitch
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Privacy warning */}
        {!privacyAcknowledged && (
          <PrivacyWarningBanner service="Stitch" onAcknowledge={acknowledgePrivacy} />
        )}

        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">Generate Screen</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Describe the interface you want to generate. Optionally seed it with findings from your research.
          </p>
        </div>

        {/* Prompt */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Design Prompt
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the screen you want to generate, e.g., 'A mobile onboarding flow with three steps showing key features, using a warm color palette and large illustrations'"
            className="w-full min-h-[120px] px-4 py-3 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-y"
          />
        </div>

        {/* Device type */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            Device Type
          </label>
          <div className="flex gap-2">
            {DEVICE_TYPES.map((dt) => (
              <button
                key={dt.value}
                onClick={() => setDeviceType(dt.value)}
                className={cn(
                  "px-4 py-2 text-sm rounded-lg border transition-colors",
                  deviceType === dt.value
                    ? "border-reclaw-500 bg-reclaw-50 dark:bg-reclaw-900/20 text-reclaw-700 dark:text-reclaw-400"
                    : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600"
                )}
              >
                {dt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Model */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Model
          </label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
          >
            {MODELS.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>

        {/* Seed findings */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Seed from Findings
            </label>
            <button
              onClick={() => setShowFindingsPicker(true)}
              className="flex items-center gap-1 text-sm text-reclaw-600 hover:text-reclaw-700 dark:text-reclaw-400 dark:hover:text-reclaw-300"
            >
              <Sparkles size={14} />
              Select Findings
            </button>
          </div>
          {seedFindings.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {seedFindings.map((id) => (
                <span
                  key={id}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-reclaw-100 dark:bg-reclaw-900/30 text-reclaw-700 dark:text-reclaw-400 rounded-full"
                >
                  {id.slice(0, 8)}...
                  <button
                    onClick={() => setSeedFindings(seedFindings.filter((f) => f !== id))}
                    className="hover:text-reclaw-900 dark:hover:text-reclaw-200"
                    aria-label={`Remove finding ${id.slice(0, 8)}`}
                  >
                    <X size={12} />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={!prompt.trim() || generating}
          className={cn(
            "w-full py-3 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2",
            prompt.trim() && !generating
              ? "bg-reclaw-600 text-white hover:bg-reclaw-700"
              : "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
          )}
        >
          {generating ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Wand2 size={16} />
              Generate Screen
            </>
          )}
        </button>

        {/* Error */}
        {error && (
          <div className="rounded-lg px-4 py-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Result preview */}
        {result && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Generated: {result.title || "Screen"}
            </h3>
            <ScreenPreview html={result.html_content} deviceType={deviceType} />
          </div>
        )}
      </div>

      {/* Findings picker modal */}
      {showFindingsPicker && activeProjectId && (
        <FindingsPicker
          projectId={activeProjectId}
          selectedIds={seedFindings}
          onConfirm={(ids) => {
            setSeedFindings(ids);
            setShowFindingsPicker(false);
          }}
          onCancel={() => setShowFindingsPicker(false)}
        />
      )}
    </div>
  );
}
