"use client";

import { RefreshCw, AlertTriangle, Terminal } from "lucide-react";

interface OllamaCheckProps {
  onRetry: () => void;
}

export default function OllamaCheck({ onRetry }: OllamaCheckProps) {
  return (
    <div className="h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
      <div className="max-w-md text-center p-8">
        <div className="w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
          <AlertTriangle size={32} className="text-amber-600" />
        </div>

        <h1 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
          LLM Provider Not Connected
        </h1>
        <p className="text-slate-500 mb-6">
          Istara needs a local LLM provider (LM Studio or Ollama) running to power the AI.
          It provides the language models that analyze your research data.
        </p>

        <div className="bg-slate-900 dark:bg-slate-800 rounded-xl p-4 text-left mb-6">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-3">
            <Terminal size={12} />
            <span>LM Studio (recommended)</span>
          </div>
          <div className="font-mono text-sm space-y-1 mb-4">
            <p className="text-slate-400"># Open LM Studio and start the local server</p>
            <p className="text-green-400">lms server start</p>
            <p className="text-slate-400 mt-2"># Load a model in the LM Studio UI</p>
          </div>
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
            <Terminal size={12} />
            <span>Or use Ollama</span>
          </div>
          <div className="font-mono text-sm space-y-1">
            <p className="text-slate-400"># Start Ollama</p>
            <p className="text-green-400">ollama serve</p>
            <p className="text-slate-400 mt-2"># Pull a model</p>
            <p className="text-green-400">ollama pull qwen3:latest</p>
          </div>
        </div>

        <button
          onClick={onRetry}
          className="flex items-center gap-2 mx-auto px-6 py-3 bg-istara-600 text-white rounded-xl hover:bg-istara-700 font-medium"
        >
          <RefreshCw size={16} />
          Check Again
        </button>

        <p className="text-xs text-slate-400 mt-4">
          Set LLM_PROVIDER=lmstudio or LLM_PROVIDER=ollama in your backend .env file.
        </p>
      </div>
    </div>
  );
}
