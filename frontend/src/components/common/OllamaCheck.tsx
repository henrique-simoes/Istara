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
          Ollama Not Connected
        </h1>
        <p className="text-slate-500 mb-6">
          ReClaw needs Ollama running locally to power the AI. It provides the language models
          that analyze your research data.
        </p>

        <div className="bg-slate-900 dark:bg-slate-800 rounded-xl p-4 text-left mb-6">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-3">
            <Terminal size={12} />
            <span>If using Docker (recommended)</span>
          </div>
          <div className="font-mono text-sm space-y-1 mb-4">
            <p className="text-slate-400"># Restart all services</p>
            <p className="text-green-400">docker compose down && docker compose up</p>
            <p className="text-slate-400 mt-2"># Pull a model</p>
            <p className="text-green-400">docker exec reclaw-ollama ollama pull qwen3:latest</p>
          </div>
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-2">
            <Terminal size={12} />
            <span>If running locally (without Docker)</span>
          </div>
          <div className="font-mono text-sm space-y-1">
            <p className="text-slate-400"># Install Ollama</p>
            <p className="text-green-400">curl -fsSL https://ollama.com/install.sh | sh</p>
            <p className="text-slate-400 mt-2"># Start Ollama</p>
            <p className="text-green-400">ollama serve</p>
            <p className="text-slate-400 mt-2"># Pull a model</p>
            <p className="text-green-400">ollama pull qwen3:latest</p>
          </div>
        </div>

        <button
          onClick={onRetry}
          className="flex items-center gap-2 mx-auto px-6 py-3 bg-reclaw-600 text-white rounded-xl hover:bg-reclaw-700 font-medium"
        >
          <RefreshCw size={16} />
          Check Again
        </button>

        <p className="text-xs text-slate-400 mt-4">
          If using Docker, Ollama starts automatically via docker-compose.
        </p>
      </div>
    </div>
  );
}
