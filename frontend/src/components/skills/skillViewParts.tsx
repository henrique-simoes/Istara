import { useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { cn } from "@/lib/utils";

export type PhaseFilter = "all" | "discover" | "define" | "develop" | "deliver";
export type Tab = "catalog" | "proposals" | "create";

export interface SkillData {
  name: string;
  display_name: string;
  description: string;
  phase: string;
  skill_type: string;
  version: string;
  enabled: boolean;
  plan_prompt?: string;
  execute_prompt?: string;
  output_schema?: string;
  changelog?: { version: string; date: string; changes: string }[];
  health?: {
    health_score: number;
    executions: number;
    success_rate: number;
    avg_quality: number;
    completeness: number;
    last_used: string | null;
    pending_proposals: number;
  };
  usage?: {
    executions: number;
    successes: number;
    failures: number;
    avg_quality: number;
    success_rate: number;
    last_used: string | null;
  };
}

export interface ProposalData {
  id: string;
  skill_name: string;
  field: string;
  current_value: string;
  proposed_value: string;
  reason: string;
  confidence: number;
  status: string;
  created_at: string;
  reviewed_at: string | null;
}

export const PHASE_COLORS: Record<string, string> = {
  discover: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  define: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  develop: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  deliver: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
};

export function showSkillToast(
  type: "info" | "success" | "warning" | "error",
  title: string,
  message: string
) {
  window.dispatchEvent(new CustomEvent("istara:toast", { detail: { type, title, message } }));
}

export function HealthBadge({ score }: { score: number }) {
  const color =
    score >= 0.7
      ? "text-green-600"
      : score >= 0.4
        ? "text-amber-500"
        : "text-red-500";
  return (
    <span className={cn("text-xs font-mono font-medium", color)}>
      {(score * 100).toFixed(0)}%
    </span>
  );
}

export function formatConfidence(confidence: number | undefined): string {
  if (confidence == null || Number.isNaN(confidence)) return "--";
  const normalized = confidence <= 1 ? confidence * 100 : confidence;
  return `${Math.max(0, Math.min(100, normalized)).toFixed(0)}%`;
}

export function SkillEditor({
  skill,
  onSave,
  onCancel,
}: {
  skill: SkillData;
  onSave: (updates: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [desc, setDesc] = useState(skill.description);
  const [planPrompt, setPlanPrompt] = useState(skill.plan_prompt || "");
  const [execPrompt, setExecPrompt] = useState(skill.execute_prompt || "");
  const [changelog, setChangelog] = useState("");

  return (
    <div className="space-y-3 pt-3 border-t border-slate-100 dark:border-slate-700">
      <div>
        <label className="text-xs font-medium text-slate-500 mb-1 block">
          Description
        </label>
        <textarea
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-istara-500 resize-none"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-slate-500 mb-1 block">
          Plan Prompt
        </label>
        <textarea
          value={planPrompt}
          onChange={(e) => setPlanPrompt(e.target.value)}
          rows={4}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-istara-500 resize-none"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-slate-500 mb-1 block">
          Execute Prompt
        </label>
        <textarea
          value={execPrompt}
          onChange={(e) => setExecPrompt(e.target.value)}
          rows={6}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-istara-500 resize-none"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-slate-500 mb-1 block">
          Changelog note
        </label>
        <input
          type="text"
          placeholder="What changed?"
          value={changelog}
          onChange={(e) => setChangelog(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-istara-500"
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={() =>
            onSave({
              description: desc,
              plan_prompt: planPrompt,
              execute_prompt: execPrompt,
              changelog_entry: changelog,
            })
          }
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-istara-600 text-white text-xs font-medium hover:bg-istara-700"
        >
          <CheckCircle2 size={12} /> Save Changes
        </button>
        <button
          onClick={onCancel}
          className="px-3 py-1.5 rounded-lg text-slate-500 text-xs hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
