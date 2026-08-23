"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  Bot,
  Check,
  ChevronDown,
  CircleHelp,
  Gauge,
  Search,
  SlidersHorizontal,
  X,
  Zap,
} from "lucide-react";
import type { ChatSession, ChatUsage, PiCatalogModel, PiCatalogProvider, PiEndpointInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ModelChoice {
  key: string;
  provider: PiCatalogProvider | null;
  model: PiCatalogModel | null;
  modelId: string;
  endpointId?: string;
  label: string;
  providerLabel: string;
  enabled: boolean;
}

function formatTokens(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(value >= 10_000 ? 0 : 1)}k`;
  return new Intl.NumberFormat().format(value);
}

function formatCost(value: number, hasData: boolean): string {
  if (!hasData) return "—";
  if (!Number.isFinite(value) || value === 0) return "$0.00";
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

function modelEffortLevels(model: PiCatalogModel | null): string[] {
  if (model?.thinkingLevels?.length) return ["server_default", ...model.thinkingLevels];
  if (model?.reasoning) return ["server_default", "off", "minimal", "low", "medium", "high", "xhigh", "max"];
  return ["server_default", "off", "auto", "on"];
}

function effortLabel(value: string): string {
  if (value === "server_default") return "Default";
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function ModelPicker({
  choices,
  selected,
  onSelect,
  onOpen,
}: {
  choices: ModelChoice[];
  selected: ModelChoice | null;
  onSelect: (choice: ModelChoice) => void;
  onOpen?: () => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const matches = normalized
      ? choices.filter((choice) => `${choice.label} ${choice.modelId} ${choice.providerLabel}`.toLowerCase().includes(normalized))
      : choices;
    return matches.slice(0, 80);
  }, [choices, query]);

  return (
    <div className="relative min-w-0">
      <button
        type="button"
        className="ui-control flex w-full min-w-0 items-center gap-2 px-3 text-left"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => { if (!open) onOpen?.(); setOpen((value) => !value); }}
      >
        <Zap size={15} className="shrink-0 text-istara-600" aria-hidden="true" />
        <span className="min-w-0 flex-1 truncate">
          <span className="block truncate text-xs font-semibold text-slate-900 dark:text-white">{selected?.label || "Choose a model"}</span>
          <span className="block truncate text-[11px] text-slate-500 dark:text-slate-400">{selected?.providerLabel || "Open the model menu"}</span>
        </span>
        <ChevronDown size={16} className={cn("shrink-0 text-slate-400 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="ui-menu absolute left-0 top-[calc(100%+8px)] z-[120] w-[min(28rem,calc(100vw-2rem))] overflow-hidden">
          <div className="border-b border-slate-200 p-2 dark:border-slate-700">
            <div className="flex items-center gap-2 rounded-lg border border-slate-300 px-2 dark:border-slate-600">
              <Search size={15} className="shrink-0 text-slate-400" aria-hidden="true" />
              <input
                autoFocus
                role="combobox"
                aria-label="Search chat models"
                aria-controls="chat-model-listbox"
                aria-activedescendant={filtered[activeIndex] ? `chat-model-option-${encodeURIComponent(filtered[activeIndex].key)}` : undefined}
                aria-expanded="true"
                value={query}
                onChange={(event) => { setQuery(event.target.value); setActiveIndex(0); }}
                onKeyDown={(event) => {
                  if (event.key === "ArrowDown") { event.preventDefault(); setActiveIndex((index) => Math.min(index + 1, Math.max(filtered.length - 1, 0))); }
                  if (event.key === "ArrowUp") { event.preventDefault(); setActiveIndex((index) => Math.max(index - 1, 0)); }
                  if (event.key === "Escape") setOpen(false);
                  if (event.key === "Enter" && filtered[activeIndex]) { event.preventDefault(); if (filtered[activeIndex].enabled) { onSelect(filtered[activeIndex]); setOpen(false); } }
                }}
                placeholder="Search providers or models"
                className="min-h-[40px] min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
              />
              <button type="button" className="ui-icon-button !min-h-[36px] !min-w-[36px]" onClick={() => { setQuery(""); setOpen(false); }} aria-label="Close model menu"><X size={15} /></button>
            </div>
            <p className="mt-2 px-1 text-[11px] text-slate-500">{query ? `${filtered.length} matches` : "Browse enabled Pi models; type to narrow the catalog."}</p>
          </div>
          <div id="chat-model-listbox" role="listbox" aria-label="Chat models" className="max-h-80 overflow-y-auto p-2">
            {filtered.length === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-slate-500">No models match that search.</p>
            ) : filtered.map((choice, index) => (
              <button
                key={choice.key}
                type="button"
                id={`chat-model-option-${encodeURIComponent(choice.key)}`}
                role="option"
                aria-selected={selected?.key === choice.key}
                aria-disabled={!choice.enabled}
                disabled={!choice.enabled}
                data-active={index === activeIndex}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => { onSelect(choice); setOpen(false); }}
                className={cn("ui-option px-3 py-2.5", !choice.enabled && "cursor-not-allowed opacity-55", selected?.key === choice.key && "bg-istara-50 dark:bg-istara-950/40")}
              >
                <span className="min-w-0 flex-1 text-left">
                  <span className="flex items-center gap-2">
                    <span className="truncate text-sm font-semibold">{choice.label}</span>
                    {selected?.key === choice.key && <Check size={15} className="shrink-0 text-istara-600" aria-hidden="true" />}
                  </span>
                  <span className="block truncate text-xs text-slate-500 dark:text-slate-400">{choice.providerLabel} · {choice.modelId}</span>
                </span>
                <span className="shrink-0 text-right text-[11px] text-slate-500 dark:text-slate-400">
                  {choice.enabled ? (choice.model?.thinkingLevels?.length ? `${choice.model.thinkingLevels.length} efforts` : "Enabled") : "Configure in Settings"}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function UsagePopover({ usage, model, open, onOpenChange }: { usage: ChatUsage | null; model: PiCatalogModel | null; open: boolean; onOpenChange: (open: boolean) => void }) {
  const data = usage?.last_turn?.usage || {};
  const currentInput = Number(data.input_tokens ?? data.input ?? usage?.latest?.input_tokens ?? 0);
  const contextWindow = model?.contextWindow || 0;
  const contextLabel = contextWindow ? `${formatTokens(currentInput)} / ${formatTokens(contextWindow)}` : `${formatTokens(currentInput)} used`;

  return (
    <div className="relative shrink-0">
      <button type="button" className="ui-control inline-flex items-center gap-2 px-3 text-xs font-semibold" onClick={() => onOpenChange(!open)} aria-expanded={open} aria-haspopup="dialog">
        <Activity size={15} className="text-istara-600" aria-hidden="true" />
        <span className="hidden sm:inline">Usage</span>
        <span className="font-mono tabular-nums">{formatTokens(usage?.total_tokens || 0)}</span>
        <ChevronDown size={14} className={cn("text-slate-400 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div role="dialog" aria-label="Chat usage details" className="ui-menu absolute right-0 top-[calc(100%+8px)] z-[120] w-[min(24rem,calc(100vw-2rem))] p-4">
          <div className="flex items-start justify-between gap-3">
            <div><h3 className="text-sm font-semibold text-slate-950 dark:text-white">This chat&apos;s usage</h3><p className="mt-1 text-xs text-slate-500">Provider-reported when available. Estimated values are labelled.</p></div>
            <button type="button" className="ui-icon-button !min-h-[36px] !min-w-[36px]" onClick={() => onOpenChange(false)} aria-label="Close usage details"><X size={15} /></button>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-2">
            {[
              ["Input", formatTokens(usage?.input_tokens || 0)],
              ["Output", formatTokens(usage?.output_tokens || 0)],
              ["Total", formatTokens(usage?.total_tokens || 0)],
              ["Cache read", formatTokens(usage?.cache_read || 0)],
              ["Cache write", formatTokens(usage?.cache_write || 0)],
              ["Cost", formatCost(usage?.cost_usd || 0, Boolean(usage?.row_count))],
              ["Context", contextLabel],
              ["Turns", String(usage?.turns || 0)],
            ].map(([label, value]) => <div key={label} className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800"><dt className="text-[11px] text-slate-500">{label}</dt><dd className="mt-1 font-mono text-sm font-semibold tabular-nums text-slate-900 dark:text-white">{value}</dd></div>)}
          </dl>
          <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-500"><span>{usage?.exact ? "Exact provider usage" : usage?.estimated ? "Contains estimates" : "No completed usage yet"}</span><span>{usage?.latest?.engine ? `Engine: ${usage.latest.engine === "pi" ? "Pi" : "Istara"}` : ""}</span></div>
          {usage?.latest?.stop_reason && <p className="mt-2 text-[11px] text-slate-500">Last stop: {usage.latest.stop_reason}</p>}
        </div>
      )}
    </div>
  );
}

export default function ChatModelControls({
  activeSession,
  agents,
  providers,
  configured,
  legacyModels,
  engine,
  usage,
  onUpdateSession,
}: {
  activeSession: ChatSession | undefined;
  agents: any[];
  providers: PiCatalogProvider[];
  configured: PiEndpointInfo[];
  legacyModels: string[];
  engine: "pi" | "legacy";
  usage: ChatUsage | null;
  onUpdateSession: (data: Record<string, unknown>) => void;
}) {
  const [agentOpen, setAgentOpen] = useState(false);
  const [usageOpen, setUsageOpen] = useState(false);

  const choices = useMemo<ModelChoice[]>(() => {
    const result: ModelChoice[] = [];
    for (const provider of providers) {
      for (const model of provider.models) {
        const endpoint = configured.find((candidate) =>
          candidate.model === model.id &&
          (!candidate.pi_provider || candidate.pi_provider === provider.id || candidate.auth_provider === provider.id)
        );
        result.push({
          key: `${provider.id}:${model.id}`,
          provider,
          model,
          modelId: model.id,
          endpointId: endpoint?.endpoint_id,
          label: model.name || model.id,
          providerLabel: provider.display_name,
          enabled: Boolean(endpoint) && engine === "pi",
        });
      }
    }
    const legacyChoices: ModelChoice[] = engine === "legacy"
      ? legacyModels.map((modelId) => ({ key: `legacy:${modelId}`, provider: null, model: null, modelId, label: modelId, providerLabel: "Istara local/server", enabled: true }))
      : [];
    const ordered = engine === "legacy"
      ? [...legacyChoices, ...result]
      : [...result.filter((choice) => choice.enabled), ...result.filter((choice) => !choice.enabled)];
    const override = activeSession?.model_override;
    if (override && !ordered.some((choice) => choice.modelId === override && (!activeSession?.endpoint_override || choice.endpointId === activeSession.endpoint_override))) {
      ordered.unshift({ key: `current:${override}`, provider: null, model: null, endpointId: activeSession?.endpoint_override || undefined, modelId: override, label: override, providerLabel: "Current session model", enabled: true });
    }
    return ordered;
  }, [activeSession, configured, engine, legacyModels, providers]);

  if (!activeSession) return null;

  const selected = (activeSession.endpoint_override ? choices.find((choice) => choice.endpointId === activeSession.endpoint_override) : undefined) || choices.find((choice) => choice.modelId === activeSession.model_override) || choices.find((choice) => choice.enabled) || null;
  const effortLevels = modelEffortLevels(selected?.model || null);
  const currentEffort = effortLevels.includes(activeSession.thinking_mode || "") ? activeSession.thinking_mode : effortLevels[0];
  const assignedAgent = agents.find((agent: any) => agent.id === activeSession.agent_id);

  const setModel = (choice: ModelChoice) => {
    const nextEffort = choice.model?.thinkingLevels?.length
      ? (choice.model.thinkingLevels.includes(activeSession.thinking_mode || "") || activeSession.thinking_mode === "server_default" ? activeSession.thinking_mode : "server_default")
      : activeSession.thinking_mode || "server_default";
    onUpdateSession({ model_override: choice.modelId, endpoint_override: choice.endpointId || null, thinking_mode: nextEffort });
  };

  return (
    <div className="border-b border-slate-200 bg-white/95 px-3 py-2.5 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-950/95 sm:px-5">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2">
        <div className="relative min-w-[11rem] max-w-full flex-1 sm:max-w-[18rem]">
          <button type="button" className="ui-control flex w-full items-center gap-2 px-3 text-left" onClick={() => { setUsageOpen(false); setAgentOpen((value) => !value); }} aria-expanded={agentOpen} aria-haspopup="listbox">
            <Bot size={15} className="shrink-0 text-slate-500" aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate text-xs font-semibold text-slate-900 dark:text-white">{assignedAgent?.name || "Istara (Main)"}</span>
            <ChevronDown size={14} className="shrink-0 text-slate-400" />
          </button>
          {agentOpen && <div role="listbox" aria-label="Choose agent" className="ui-menu absolute left-0 top-[calc(100%+8px)] z-[120] w-64 p-2">
            <button type="button" role="option" aria-selected={!activeSession.agent_id} className="ui-option px-3 py-2 text-sm" onClick={() => { onUpdateSession({ agent_id: null }); setAgentOpen(false); }}>Istara (Main)</button>
            {agents.filter((agent: any) => agent.is_active && agent.id !== "istara-main").map((agent: any) => <button key={agent.id} type="button" role="option" aria-selected={activeSession.agent_id === agent.id} className="ui-option px-3 py-2 text-sm" onClick={() => { onUpdateSession({ agent_id: agent.id }); setAgentOpen(false); }}>{agent.name}</button>)}
          </div>}
        </div>
        <div className="hidden h-7 w-px bg-slate-200 dark:bg-slate-700 sm:block" aria-hidden="true" />
        <div className="min-w-[15rem] max-w-full flex-[1.5] sm:max-w-[28rem]"><ModelPicker choices={choices} selected={selected} onSelect={setModel} onOpen={() => { setUsageOpen(false); setAgentOpen(false); }} /></div>
        <div className="flex min-w-[10rem] items-center gap-2">
          <SlidersHorizontal size={15} className="hidden text-slate-500 sm:block" aria-hidden="true" />
          <label htmlFor="chat-effort" className="sr-only">Model effort</label>
          <select id="chat-effort" value={currentEffort} onChange={(event) => onUpdateSession({ thinking_mode: event.target.value })} className="ui-control min-w-0 flex-1 px-3 text-xs font-semibold">
            {effortLevels.map((level) => <option key={level} value={level}>{effortLabel(level)}</option>)}
          </select>
        </div>
        <UsagePopover usage={usage} model={selected?.model || null} open={usageOpen} onOpenChange={(open) => { setUsageOpen(open); if (open) setAgentOpen(false); }} />
      </div>
      <div className="mx-auto mt-2 flex max-w-6xl flex-wrap items-center gap-x-3 gap-y-1 px-1 text-[11px] text-slate-500 dark:text-slate-400">
        <span className="inline-flex items-center gap-1"><Gauge size={13} className="text-istara-600" /> Core: <strong className="text-slate-700 dark:text-slate-200">{engine === "pi" ? "Pi" : "Istara"}</strong></span>
        <span className="hidden sm:inline">·</span>
        <span className="inline-flex items-center gap-1"><Gauge size={13} className="text-istara-600" /> Effort: <strong className="text-slate-700 dark:text-slate-200">{effortLabel(currentEffort)}</strong></span>
        <span className="hidden sm:inline">·</span>
        <span className="inline-flex items-center gap-1"><CircleHelp size={13} /> {selected?.model?.thinkingLevels?.length ? `${selected.model.thinkingLevels.length} provider-native levels` : "Server-compatible controls"}</span>
        {usage?.last_turn?.model && <><span className="hidden sm:inline">·</span><span className="truncate">Last turn: {usage.last_turn.model}</span></>}
        {engine !== "pi" && <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">Istara local/server model choices</span>}
        {usage?.estimated && <span className="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-800 dark:bg-amber-950/50 dark:text-amber-200">Contains estimates</span>}
      </div>
    </div>
  );
}
