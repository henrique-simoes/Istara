"use client";

import { useCallback, useEffect, useId, useState } from "react";
import {
  AlertTriangle,
  Cloud,
  Gauge,
  HardDrive,
  KeyRound,
  Loader2,
  LockKeyhole,
  Plug,
  Scale,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { decisionModels } from "@/lib/api";
import type {
  DecisionModelCheckResult,
  DecisionModelEndpoint,
  DecisionModelPreset,
} from "@/lib/catalogTypes";
import {
  DECISION_MODEL_EXPLAINER,
  FIRST_ACTIVATION_STEPS,
  decisionModelErrorMessage,
  isAliasModelId,
} from "@/lib/decisionModelCopy";
import { cn } from "@/lib/utils";
import { useRoleCapabilities } from "@/hooks/useRoleCapabilities";

const PRINCIPLE_ICONS = [Gauge, ShieldCheck, LockKeyhole];

const inputClass =
  "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ui-focus)] dark:border-slate-600 dark:bg-slate-900 dark:text-white";

function LocalityBadge({ locality }: { locality: "local" | "hosted" }) {
  const Icon = locality === "hosted" ? Cloud : HardDrive;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        locality === "hosted"
          ? "border-sky-300 bg-sky-50 text-sky-800 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200"
          : "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200"
      )}
    >
      <Icon size={12} aria-hidden="true" />
      {locality === "hosted" ? "Hosted (cloud)" : "Local"}
    </span>
  );
}

function CredentialBadge({ status }: { status: DecisionModelEndpoint["credential_status"] }) {
  if (status === "not_needed") return null;
  const missing = status === "missing";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        missing
          ? "border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200"
          : "border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
      )}
    >
      <KeyRound size={12} aria-hidden="true" />
      {missing ? "API key missing" : "API key stored"}
    </span>
  );
}

export function DecisionModelExplainer({ headingLevel = "h3" }: { headingLevel?: "h2" | "h3" }) {
  const Heading = headingLevel;
  return (
    <div>
      <Heading className="text-sm font-semibold text-slate-900 dark:text-white">{DECISION_MODEL_EXPLAINER.title}</Heading>
      <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">{DECISION_MODEL_EXPLAINER.lead}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {DECISION_MODEL_EXPLAINER.principles.map((principle, index) => {
          const Icon = PRINCIPLE_ICONS[index] || ShieldCheck;
          return (
            <div key={principle.title} className="flex gap-2 rounded-lg bg-slate-50 px-3 py-3 dark:bg-slate-900">
              <Icon size={17} className="mt-0.5 shrink-0 text-istara-600 dark:text-istara-300" aria-hidden="true" />
              <p className="text-xs leading-5 text-slate-600 dark:text-slate-300">
                <strong className="text-slate-900 dark:text-white">{principle.title}.</strong> {principle.body}
              </p>
            </div>
          );
        })}
      </div>
      <p className="mt-3 max-w-3xl text-xs leading-5 text-slate-500 dark:text-slate-400">{DECISION_MODEL_EXPLAINER.trust}</p>
    </div>
  );
}

interface FormState {
  endpoint_id: string;
  base_url: string;
  model: string;
  api_key: string;
  locality: "local" | "hosted";
}

function formFromPreset(preset: DecisionModelPreset): FormState {
  return {
    endpoint_id: preset.preset_id === "typesafe-jev" ? "jev" : "local-decider",
    base_url: preset.base_url,
    model: preset.model,
    api_key: "",
    locality: preset.locality,
  };
}

function FirstActivationGuide() {
  return (
    <div className="rounded-xl border border-dashed border-istara-300 bg-istara-50/50 p-4 dark:border-istara-800 dark:bg-istara-950/30">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Set up your first decision model</h3>
      <ol className="mt-3 grid gap-3 md:grid-cols-2">
        {FIRST_ACTIVATION_STEPS.map((step, index) => (
          <li key={step.title} className="flex gap-3">
            <span aria-hidden="true" className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-istara-600 text-xs font-semibold text-white">
              {index + 1}
            </span>
            <span className="text-xs leading-5 text-slate-600 dark:text-slate-300">
              <strong className="block text-sm text-slate-900 dark:text-white">{step.title}</strong>
              {step.body}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function checkMessage(result: DecisionModelCheckResult): string {
  if (!result.ok) return `Not reachable: ${decisionModelErrorMessage(new Error(result.reason || ""), "unknown error")}`;
  const served = result.served_model || "an unnamed model";
  const differs = result.served_model && result.served_model !== result.requested_model;
  return `Connected. Answered by ${served}${differs ? ` (requested ${result.requested_model})` : ""}.`;
}

function EndpointActions({ endpoint, onRemoved }: { endpoint: DecisionModelEndpoint; onRemoved: (error?: string) => void }) {
  const [result, setResult] = useState<DecisionModelCheckResult | "running" | null>(null);
  const [confirming, setConfirming] = useState(false);

  const check = async () => {
    setResult("running");
    try {
      setResult(await decisionModels.check(endpoint.endpoint_id));
    } catch (error) {
      setResult({ ok: false, reason: decisionModelErrorMessage(error, "Check failed.") });
    }
  };

  const remove = async () => {
    setConfirming(false);
    try {
      await decisionModels.remove(endpoint.endpoint_id);
      onRemoved();
    } catch (error) {
      onRemoved(decisionModelErrorMessage(error, "Could not remove the decision model."));
    }
  };

  const running = result === "running";
  return (
    <>
      <div className="flex shrink-0 flex-wrap gap-2">
        <button type="button" onClick={() => void check()} disabled={running} className="secondary-action inline-flex items-center gap-1.5 text-xs">
          {running ? <Loader2 size={13} className="animate-spin" aria-hidden="true" /> : <Plug size={13} aria-hidden="true" />}
          Check connection
        </button>
        {confirming ? (
          <>
            <button
              type="button"
              onClick={() => void remove()}
              className="inline-flex min-h-[36px] items-center rounded-lg bg-red-700 px-3 text-xs font-semibold text-white hover:bg-red-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ui-focus)]"
            >
              Remove and delete key
            </button>
            <button type="button" onClick={() => setConfirming(false)} className="secondary-action text-xs">
              Keep
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="secondary-action inline-flex items-center gap-1.5 text-xs"
            aria-label={`Remove ${endpoint.endpoint_id}`}
          >
            <Trash2 size={13} aria-hidden="true" /> Remove
          </button>
        )}
      </div>
      {result && !running && (
        <p
          role="status"
          className={cn(
            "mt-3 w-full rounded-lg px-3 py-2 text-xs",
            result.ok
              ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200"
              : "bg-red-50 text-red-800 dark:bg-red-950/40 dark:text-red-200"
          )}
        >
          {checkMessage(result)}
        </p>
      )}
    </>
  );
}

function EndpointRow({ endpoint, onRemoved }: { endpoint: DecisionModelEndpoint; onRemoved: (error?: string) => void }) {
  return (
    <li className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-slate-900 dark:text-white">{endpoint.endpoint_id}</span>
            <LocalityBadge locality={endpoint.locality} />
            <CredentialBadge status={endpoint.credential_status} />
          </p>
          <p className="mt-1 break-all font-mono text-xs text-slate-500 dark:text-slate-400">
            {endpoint.model} · {endpoint.base_url}
          </p>
          {endpoint.model_is_alias && (
            <p className="mt-2 flex items-start gap-1.5 text-xs text-amber-800 dark:text-amber-200">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
              This is a moving alias. Its behaviour can change without notice, so it will never become trusted. Pin a version such
              as jev-1.14.0.
            </p>
          )}
        </div>
        <EndpointActions endpoint={endpoint} onRemoved={onRemoved} />
      </div>
    </li>
  );
}

function PresetPicker({ presets, onPick }: { presets: DecisionModelPreset[]; onPick: (preset: DecisionModelPreset) => void }) {
  return (
    <div className="grid gap-3 md:grid-cols-2" aria-label="Add a decision model">
      {presets.map((preset) => {
        const hosted = preset.locality === "hosted";
        const Icon = hosted ? Cloud : HardDrive;
        return (
          <button
            key={preset.preset_id}
            type="button"
            onClick={() => onPick(preset)}
            className="flex min-w-0 items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 text-left transition-colors hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ui-focus)] dark:border-slate-700 dark:bg-slate-900/40 dark:hover:bg-slate-800"
          >
            <Icon size={18} className={cn("mt-0.5 shrink-0", hosted ? "text-sky-600" : "text-emerald-600")} aria-hidden="true" />
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-slate-900 dark:text-white">Add {preset.label}</span>
              <span className="mt-1 block text-xs leading-5 text-slate-600 dark:text-slate-300">
                {hosted
                  ? "Needs an API key from TypeSafe. Projects must opt in before any data is sent."
                  : "Runs on your own hardware. No key and no cloud consent needed."}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function EndpointForm({ initial, onSaved, onCancel }: { initial: FormState; onSaved: () => void; onCancel: () => void }) {
  const formId = useId();
  const [form, setForm] = useState<FormState>(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hosted = form.locality === "hosted";
  const alias = isAliasModelId(form.model);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await decisionModels.add({
        endpoint_id: form.endpoint_id.trim(),
        base_url: form.base_url.trim(),
        model: form.model.trim(),
        api_key: form.api_key,
      });
      onSaved();
    } catch (err) {
      setError(decisionModelErrorMessage(err, "Could not add the decision model."));
    } finally {
      setSaving(false);
    }
  };

  const field = (key: keyof FormState) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: event.target.value });

  return (
    <form onSubmit={submit} className="rounded-xl border border-slate-200 p-4 dark:border-slate-700" aria-labelledby={`${formId}-title`}>
      <h3 id={`${formId}-title`} className="text-sm font-semibold text-slate-900 dark:text-white">
        {hosted ? "Add a hosted decision model" : "Add a local decision model"}
      </h3>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <label className="text-xs font-medium text-slate-700 dark:text-slate-200">
          Name
          <input required pattern="[A-Za-z0-9][A-Za-z0-9_.\-]*" maxLength={64} value={form.endpoint_id} onChange={field("endpoint_id")} className={inputClass} />
        </label>
        <label className="text-xs font-medium text-slate-700 dark:text-slate-200">
          Model version
          <input
            required
            value={form.model}
            placeholder={hosted ? "jev-1.14.0" : "the model your server loads"}
            onChange={field("model")}
            className={inputClass}
            aria-describedby={alias ? `${formId}-alias` : undefined}
          />
          {alias && (
            <span id={`${formId}-alias`} className="mt-1 block font-normal text-amber-800 dark:text-amber-200">
              Moving aliases can change without notice and never become trusted. Prefer a pinned version.
            </span>
          )}
        </label>
        <label className="text-xs font-medium text-slate-700 dark:text-slate-200 md:col-span-2">
          Server address
          <input required type="url" value={form.base_url} onChange={field("base_url")} className={inputClass} />
          <span className="mt-1 block font-normal text-slate-500 dark:text-slate-400">
            Istara calls this address at /v1/systemone. Public addresses must use HTTPS.
          </span>
        </label>
        <label className="text-xs font-medium text-slate-700 dark:text-slate-200 md:col-span-2">
          API key {!hosted && <span className="font-normal text-slate-500">(optional for local servers)</span>}
          <input type="password" autoComplete="off" required={hosted} value={form.api_key} onChange={field("api_key")} className={inputClass} />
          <span className="mt-1 block font-normal text-slate-500 dark:text-slate-400">
            Stored in the macOS Keychain, or the server&apos;s secret store elsewhere. It is never shown again.
          </span>
        </label>
      </div>
      {error && (
        <p role="alert" className="mt-3 text-sm font-medium text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="submit" disabled={saving} className="primary-action inline-flex items-center gap-1.5 text-sm">
          {saving && <Loader2 size={14} className="animate-spin" aria-hidden="true" />}
          Add decision model
        </button>
        <button type="button" onClick={onCancel} className="secondary-action text-sm">
          Cancel
        </button>
      </div>
    </form>
  );
}

function SectionHeader() {
  return (
    <div className="border-b border-slate-200 px-5 py-5 dark:border-slate-700 sm:px-6">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-istara-100 text-istara-700 dark:bg-istara-950/60 dark:text-istara-300">
          <Scale size={20} aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-istara-700 dark:text-istara-300">Assurance</p>
          <h2 id="decision-models-title" className="mt-1 text-xl font-semibold tracking-tight text-slate-950 dark:text-white">
            Decision models
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Optional. Nothing here is turned on for any project until a project administrator chooses it in Project Settings.
          </p>
        </div>
      </div>
      <div className="mt-5">
        <DecisionModelExplainer />
      </div>
    </div>
  );
}

/** Global-admin configuration; renders nothing for other roles. */
export default function DecisionModelsSection() {
  const capabilities = useRoleCapabilities();
  if (!capabilities.canManageLlmInfrastructure) return null;
  return <DecisionModelsManager />;
}

function DecisionModelsManager() {
  const [endpoints, setEndpoints] = useState<DecisionModelEndpoint[]>([]);
  const [presets, setPresets] = useState<DecisionModelPreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await decisionModels.list();
      setEndpoints(data.endpoints);
      setPresets(data.presets);
    } catch (error) {
      setLoadError(decisionModelErrorMessage(error, "Could not load decision models."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const ready = !loading && !loadError;
  const afterRemove = (error?: string) => (error ? setLoadError(error) : void load());

  return (
    <section id="tour-target-decision-models" className="ui-panel overflow-visible" aria-labelledby="decision-models-title">
      <SectionHeader />
      <div className="space-y-4 px-5 py-5 sm:px-6">
        {loading && (
          <p className="flex items-center gap-2 text-sm text-slate-500" role="status">
            <Loader2 size={15} className="animate-spin" aria-hidden="true" /> Loading decision models…
          </p>
        )}
        {loadError && (
          <div role="alert" className="flex items-start justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
            <span>{loadError}</span>
            <button type="button" onClick={() => void load()} className="secondary-action shrink-0 text-xs">
              Retry
            </button>
          </div>
        )}
        {ready && endpoints.length === 0 && !form && <FirstActivationGuide />}
        {ready && endpoints.length > 0 && (
          <ul className="space-y-3" aria-label="Configured decision models">
            {endpoints.map((endpoint) => (
              <EndpointRow key={endpoint.endpoint_id} endpoint={endpoint} onRemoved={afterRemove} />
            ))}
          </ul>
        )}
        {ready && !form && <PresetPicker presets={presets} onPick={(preset) => setForm(formFromPreset(preset))} />}
        {form && (
          <EndpointForm
            initial={form}
            onCancel={() => setForm(null)}
            onSaved={() => {
              setForm(null);
              void load();
            }}
          />
        )}
      </div>
    </section>
  );
}
