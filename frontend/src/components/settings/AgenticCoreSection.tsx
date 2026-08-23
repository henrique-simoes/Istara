"use client";

import { useState } from "react";
import { Check, Info, LockKeyhole, Route, ShieldCheck, Sparkles } from "lucide-react";
import { cn, agentEngineLabel } from "@/lib/utils";
import {
  ENGINE_COMPARATIVE_SUMMARIES,
  SHARED_EMBEDDING_IDENTITY_LABEL,
} from "@/lib/modelCatalog";

export interface AgenticCoreSectionProps {
  value: "pi" | "legacy" | "";
  inheritedEngine?: "pi" | "legacy";
  scope: "global" | "project";
  canManage: boolean;
  onChange: (engine: "pi" | "legacy" | "") => Promise<void> | void;
}

function EngineOption({
  engine,
  selected,
  disabled,
  saving,
  onChange,
}: {
  engine: "pi" | "legacy" | "";
  selected: boolean;
  disabled: boolean;
  saving: boolean;
  onChange: () => void;
}) {
  const entry = engine ? ENGINE_COMPARATIVE_SUMMARIES.find((item) => item.engine === engine) : null;
  const title = engine ? entry?.title || agentEngineLabel(engine) : "Inherit the global default";
  const description = engine
    ? entry?.shortDescription
    : "Let this project follow the default Agentic Core chosen by the administrator.";
  const bestFor = engine ? entry?.bestFor : "Use this when one global policy should govern every project.";

  return (
    <label
      className={cn(
        "relative flex min-w-0 cursor-pointer gap-4 rounded-xl border p-4 transition-colors",
        selected
          ? "border-istara-500 bg-istara-50/70 dark:border-istara-400 dark:bg-istara-950/40"
          : "border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900/40 dark:hover:bg-slate-800",
        disabled && "cursor-not-allowed opacity-65"
      )}
    >
      <input
        type="radio"
        name="agentic-core-choice"
        value={engine}
        checked={selected}
        disabled={disabled || saving}
        onChange={onChange}
        className="peer sr-only"
      />
      <span
        aria-hidden="true"
        className={cn(
          "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2",
          selected ? "border-istara-600 bg-istara-600 text-white" : "border-slate-300 dark:border-slate-600",
          "peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-blue-600"
        )}
      >
        {selected && <Check size={13} strokeWidth={3} />}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-base font-semibold text-slate-950 dark:text-white">{title}</span>
          {selected && <span className="rounded-full bg-istara-600 px-2 py-0.5 text-[11px] font-semibold text-white">Selected</span>}
          {engine && entry?.provisional && (
            <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
              Provisional benchmark
            </span>
          )}
        </span>
        <span className="mt-1 block text-sm leading-6 text-slate-600 dark:text-slate-300">{description}</span>
        <span className="mt-2 block text-xs font-medium leading-5 text-slate-500 dark:text-slate-400">
          Best for: <span className="font-normal">{bestFor}</span>
        </span>
      </span>
      {saving && selected && <span className="text-xs text-slate-500">Saving…</span>}
    </label>
  );
}

export default function AgenticCoreSection({
  value,
  inheritedEngine = "legacy",
  scope,
  canManage,
  onChange,
}: AgenticCoreSectionProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const effectiveEngine = value || inheritedEngine;
  const selectedEntry = ENGINE_COMPARATIVE_SUMMARIES.find((entry) => entry.engine === effectiveEngine);

  const choose = async (engine: "pi" | "legacy" | "") => {
    if (!canManage || saving || engine === value) return;
    setSaving(true);
    setError(null);
    try {
      await onChange(engine);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the Agentic Core choice.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="ui-panel overflow-visible" aria-labelledby={`agentic-core-${scope}-title`}>
      <div className="border-b border-slate-200 px-5 py-5 dark:border-slate-700 sm:px-6">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-istara-100 text-istara-700 dark:bg-istara-950/60 dark:text-istara-300">
            <Route size={20} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-istara-700 dark:text-istara-300">Core routing</p>
            <h2 id={`agentic-core-${scope}-title`} className="mt-1 text-xl font-semibold tracking-tight text-slate-950 dark:text-white">
              Choose your Agentic Core
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
              This decides which execution system handles agentic chat, tools, and model calls. You can change it later;
              your projects, evidence, and embedding space remain separate from this choice.
            </p>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3" aria-label="Agentic Core principles">
          <div className="flex gap-2 rounded-lg bg-slate-50 px-3 py-3 dark:bg-slate-900">
            <ShieldCheck size={17} className="mt-0.5 shrink-0 text-istara-600" aria-hidden="true" />
            <p className="text-xs leading-5 text-slate-600 dark:text-slate-300"><strong className="text-slate-900 dark:text-white">Same safeguards.</strong> Research validity and permissions apply to both.</p>
          </div>
          <div className="flex gap-2 rounded-lg bg-slate-50 px-3 py-3 dark:bg-slate-900">
            <Sparkles size={17} className="mt-0.5 shrink-0 text-istara-600" aria-hidden="true" />
            <p className="text-xs leading-5 text-slate-600 dark:text-slate-300"><strong className="text-slate-900 dark:text-white">Different strengths.</strong> Pi favors governed cloud model choice; Istara favors local and donated compute.</p>
          </div>
          <div className="flex gap-2 rounded-lg bg-slate-50 px-3 py-3 dark:bg-slate-900">
            <LockKeyhole size={17} className="mt-0.5 shrink-0 text-istara-600" aria-hidden="true" />
            <p className="text-xs leading-5 text-slate-600 dark:text-slate-300"><strong className="text-slate-900 dark:text-white">Safe to switch.</strong> Embedding identity is shared and never changes here.</p>
          </div>
        </div>
      </div>

      <div className="space-y-3 px-5 py-5 sm:px-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Execution choice</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {scope === "global" ? "Applies by default to every project." : "Overrides the global default for this project."}
            </p>
          </div>
          {!canManage && <span className="text-xs font-medium text-slate-500">View only</span>}
        </div>
        <div role="radiogroup" aria-labelledby={`agentic-core-${scope}-title`} className="grid gap-3 lg:grid-cols-2">
          {scope === "project" && (
            <EngineOption
              engine=""
              selected={!value}
              disabled={!canManage}
              saving={saving}
              onChange={() => void choose("")}
            />
          )}
          <EngineOption engine="pi" selected={value === "pi"} disabled={!canManage} saving={saving} onChange={() => void choose("pi")} />
          <EngineOption engine="legacy" selected={value === "legacy"} disabled={!canManage} saving={saving} onChange={() => void choose("legacy")} />
        </div>
        {error && <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">{error}</p>}

        {selectedEntry && (
          <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/60">
            <div className="flex items-start gap-2">
              <Info size={17} className="mt-0.5 shrink-0 text-slate-500" aria-hidden="true" />
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">What the latest comparison tells us</h3>
                <p className="mt-1 text-xs leading-5 text-slate-600 dark:text-slate-300">{selectedEntry.summary}</p>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4" aria-label={`${selectedEntry.title} benchmark snapshot`}>
                  {selectedEntry.benchmarkRows.map((row) => (
                    <div key={row.label} className="rounded-lg bg-white px-3 py-2 dark:bg-slate-800">
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">{row.label}</p>
                      <p className="mt-1 font-mono text-sm font-semibold tabular-nums text-slate-900 dark:text-white">{row.value}</p>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[11px] leading-5 text-slate-500 dark:text-slate-400">
                  Snapshot as of {selectedEntry.asOf}. No judged axis reached significance at 95% CI. This is provisional comparative context,
                  not accepted research evidence. Sources: {selectedEntry.provenance.join(" · ")}.
                </p>
              </div>
            </div>
          </div>
        )}

        <p className="flex items-start gap-2 border-t border-slate-200 pt-4 text-xs leading-5 text-slate-500 dark:border-slate-700 dark:text-slate-400">
          <LockKeyhole size={15} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span><strong className="text-slate-700 dark:text-slate-200">Shared embedding space.</strong> {SHARED_EMBEDDING_IDENTITY_LABEL}</span>
        </p>
      </div>
    </section>
  );
}
