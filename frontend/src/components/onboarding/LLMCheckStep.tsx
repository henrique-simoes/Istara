"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, AlertTriangle, ExternalLink, Loader2 } from "lucide-react";

/**
 * Onboarding step: check if a local LLM provider is running.
 * Non-blocking — user can skip even if no LLM is detected.
 */
export default function LLMCheckStep() {
  const [checking, setChecking] = useState(true);
  const [provider, setProvider] = useState<"lmstudio" | "ollama" | null>(null);
  const [modelCount, setModelCount] = useState(0);

  useEffect(() => {
    async function detect() {
      // Try LM Studio first
      try {
        const res = await fetch("http://localhost:1234/v1/models", { signal: AbortSignal.timeout(3000) });
        if (res.ok) {
          const data = await res.json();
          setProvider("lmstudio");
          setModelCount((data.data || []).length);
          setChecking(false);
          return;
        }
      } catch {}
      // Try Ollama
      try {
        const res = await fetch("http://localhost:11434/api/tags", { signal: AbortSignal.timeout(3000) });
        if (res.ok) {
          const data = await res.json();
          setProvider("ollama");
          setModelCount((data.models || []).length);
          setChecking(false);
          return;
        }
      } catch {}
      setChecking(false);
    }
    detect();
  }, []);

  if (checking) {
    return (
      <div className="flex items-center justify-center py-8 gap-3 text-slate-500">
        <Loader2 size={20} className="animate-spin" />
        Checking for local LLM server...
      </div>
    );
  }

  if (provider) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
          <CheckCircle2 size={24} className="text-green-600 shrink-0" />
          <div>
            <p className="text-sm font-medium text-green-800 dark:text-green-300">
              {provider === "lmstudio" ? "LM Studio" : "Ollama"} detected
            </p>
            <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">
              {modelCount} model{modelCount !== 1 ? "s" : ""} available. Ready for research.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
        <AlertTriangle size={24} className="text-amber-600 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
            No local LLM server detected
          </p>
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-1 leading-relaxed">
            ReClaw needs a local LLM to power its AI agents. Install one of these:
          </p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <a
          href="https://lmstudio.ai"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-sm"
        >
          <ExternalLink size={14} className="text-reclaw-500" />
          <div>
            <span className="font-medium text-slate-900 dark:text-white">LM Studio</span>
            <span className="block text-xs text-slate-400">GUI, easy setup</span>
          </div>
        </a>
        <a
          href="https://ollama.com"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-sm"
        >
          <ExternalLink size={14} className="text-reclaw-500" />
          <div>
            <span className="font-medium text-slate-900 dark:text-white">Ollama</span>
            <span className="block text-xs text-slate-400">CLI, lightweight</span>
          </div>
        </a>
      </div>
      <p className="text-xs text-slate-400 text-center">
        You can skip this for now and configure later in Settings.
      </p>
    </div>
  );
}
