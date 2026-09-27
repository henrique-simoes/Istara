"use client";

import { FileQuestion, Link2, ListChecks, Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SurveyIntegration } from "@/lib/types";

const PLATFORM_META: Record<string, { label: string; color: string; bg: string }> = {
  surveymonkey: { label: "Survey Platform", color: "text-[#00BF6F]", bg: "bg-[#00BF6F]/10" },
  google_forms: { label: "Web Form", color: "text-[#673AB7] dark:text-purple-300", bg: "bg-[#673AB7]/10" },
  typeform: { label: "Questionnaire Service", color: "text-slate-800 dark:text-slate-200", bg: "bg-slate-100 dark:bg-slate-800" },
};

const PRIMARY =
  "bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 dark:disabled:bg-slate-800 dark:disabled:text-slate-500 transition-colors";

export type SurveyMode = "platforms" | "studio";

export function SurveysHeader({ canManage, disabled, onConnect }: { canManage: boolean; disabled: boolean; onConnect: () => void }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Survey Platforms</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Connect external survey tools to import response data.</p>
      </div>
      <button onClick={onConnect} disabled={disabled} className={cn("flex items-center gap-1.5 px-3 py-2 text-sm", PRIMARY)}>
        <Plus size={14} />
        {canManage ? "Connect Platform" : "Request Platform"}
      </button>
    </div>
  );
}

export function InlineStatus({ notice, error }: { notice: string | null; error: string | null }) {
  if (error) return <p role="alert" className="text-xs text-red-600 dark:text-red-400">{error}</p>;
  if (notice) return <p role="status" className="text-xs text-slate-600 dark:text-slate-300">{notice}</p>;
  return null;
}

export function SurveyModeTabs({
  mode,
  platformCount,
  onChange,
}: {
  mode: SurveyMode;
  platformCount: number;
  onChange: (mode: SurveyMode) => void;
}) {
  const tab = (active: boolean, activeClass: string) =>
    cn(
      "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
      active ? activeClass : "text-slate-600 hover:text-slate-800 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
    );
  return (
    <div role="tablist" aria-label="Survey sources" className="flex flex-wrap items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
      <button
        role="tab"
        aria-selected={mode === "platforms"}
        onClick={() => onChange("platforms")}
        className={tab(mode === "platforms", "bg-istara-50 text-istara-700 dark:bg-istara-950/50 dark:text-istara-300")}
      >
        <Link2 size={13} />
        Connected Platforms & Sync ({platformCount})
      </button>
      <button
        role="tab"
        aria-selected={mode === "studio"}
        onClick={() => onChange("studio")}
        className={tab(mode === "studio", "bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300")}
      >
        <ListChecks size={13} className="text-purple-500" />
        Questionnaire Studio
      </button>
    </div>
  );
}

function PlatformCard({ integration, onRemove }: { integration: SurveyIntegration; onRemove: (id: string) => void }) {
  const meta = PLATFORM_META[integration.platform] || { label: integration.platform, color: "text-slate-600", bg: "bg-slate-100" };
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
      <div className="flex items-start justify-between mb-3">
        <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full", meta.bg, meta.color)}>{meta.label}</span>
        <button
          onClick={() => onRemove(integration.id)}
          aria-label={`Remove ${integration.name}`}
          className="p-1 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
        >
          <Trash2 size={14} />
        </button>
      </div>
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-1">{integration.name}</h3>
      <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
        <span className={cn("w-2 h-2 rounded-full", integration.is_active ? "bg-green-500" : "bg-slate-300")} />
        {integration.is_active ? "Connected" : "Disconnected"}
      </div>
      {integration.last_sync_at && (
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
          Last sync: {new Date(integration.last_sync_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}

export default function SurveyPlatformCards({
  loading,
  integrations,
  canManage,
  projectId,
  onConnect,
  onRemove,
}: {
  loading: boolean;
  integrations: SurveyIntegration[];
  canManage: boolean;
  projectId: string | null;
  onConnect: () => void;
  onRemove: (id: string) => void;
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-32 rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse" />
        ))}
      </div>
    );
  }
  if (integrations.length === 0) {
    return (
      <div className="text-center py-12 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
        <FileQuestion size={40} className="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">No external survey platforms connected</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
          Connect an external platform, or record answers a participant gave you another way in the Questionnaire Studio.
        </p>
        <button onClick={onConnect} disabled={!projectId} className={cn("px-4 py-2 text-sm", PRIMARY)}>
          {canManage ? "Connect First Platform" : "Request Platform Access"}
        </button>
      </div>
    );
  }
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {integrations.map((integration) => (
        <PlatformCard key={integration.id} integration={integration} onRemove={onRemove} />
      ))}
    </div>
  );
}
