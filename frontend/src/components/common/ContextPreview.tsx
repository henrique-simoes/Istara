"use client";

import { useEffect, useState } from "react";
import { Eye, EyeOff, Loader2, Brain, ChevronDown, ChevronRight } from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * "What I know" preview — shows the composed context the agent sees.
 * Helps users verify their context layers are working correctly.
 */
export default function ContextPreview() {
  const { activeProjectId } = useProjectStore();
  const [composedContext, setComposedContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchComposed = async () => {
    if (!activeProjectId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/contexts/composed/${activeProjectId}`);
      if (!res.ok) throw new Error("Failed to load");
      const data = await res.json();
      setComposedContext(data.composed_context || "No context configured yet.");
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (expanded && activeProjectId) {
      fetchComposed();
    }
  }, [expanded, activeProjectId]);

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Brain size={20} className="text-reclaw-600" />
          <div className="text-left">
            <h3 className="font-medium text-slate-900 dark:text-white text-sm">
              What the Agent Knows
            </h3>
            <p className="text-xs text-slate-500">
              Preview the full composed context the agent uses for every response
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {expanded ? (
            <EyeOff size={16} className="text-slate-400" />
          ) : (
            <Eye size={16} className="text-slate-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-200 dark:border-slate-700 p-4">
          {loading ? (
            <div className="flex items-center gap-2 text-slate-400 py-4 justify-center">
              <Loader2 size={16} className="animate-spin" /> Loading context...
            </div>
          ) : error ? (
            <div className="text-sm text-red-500 py-2">⚠️ {error}</div>
          ) : (
            <div className="max-h-96 overflow-y-auto">
              <pre className="text-xs text-slate-600 dark:text-slate-400 whitespace-pre-wrap font-mono leading-relaxed bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
                {composedContext}
              </pre>
              <p className="text-[10px] text-slate-400 mt-2">
                {composedContext.length.toLocaleString()} characters • Composed from all active context layers
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
