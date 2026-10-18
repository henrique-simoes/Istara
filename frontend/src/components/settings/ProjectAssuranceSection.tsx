"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Cloud, HardDrive, Loader2, ShieldCheck } from "lucide-react";
import { decisionModels } from "@/lib/api";
import type { AssuranceMode, ProjectDecisionPolicy, ProjectDecisionPolicyRequest } from "@/lib/catalogTypes";
import {
  ASSURANCE_MODE_COPY,
  LLM_METHOD_LABELS,
  TRUST_STATUS_COPY,
  decisionModelErrorMessage,
} from "@/lib/decisionModelCopy";
import { DecisionModelExplainer } from "@/components/settings/DecisionModelsSection";
import { cn } from "@/lib/utils";

const TRUST_MIN_LABELS = 50;
const USES_DECIDERS: AssuranceMode[] = ["decision_models", "both"];
const CHOOSES_LLM_METHOD: AssuranceMode[] = ["llm_judges", "both"];

type Draft = ProjectDecisionPolicyRequest;
type Endpoint = ProjectDecisionPolicy["available_endpoints"][number];
type TrustScope = NonNullable<ProjectDecisionPolicy["trust"]>[number];

function toRequest(policy: ProjectDecisionPolicy): Draft {
  return {
    mode: policy.mode,
    llm_method: policy.llm_method,
    llm_judges: policy.llm_judges,
    decider_endpoint_ids: policy.decider_endpoint_ids,
    hosted_egress_endpoint_ids: policy.hosted_egress_endpoint_ids,
  };
}

function toggle(list: string[], id: string, on: boolean): string[] {
  return on ? Array.from(new Set([...list, id])) : list.filter((item) => item !== id);
}

function ModeCard({
  mode,
  group,
  selected,
  disabled,
  onSelect,
}: {
  mode: AssuranceMode;
  group: string;
  selected: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  return (
    <label
      className={cn(
        "relative flex min-w-0 cursor-pointer gap-3 rounded-xl border p-4 transition-colors",
        selected
          ? "border-istara-600 bg-istara-50/70 dark:border-istara-400 dark:bg-istara-950/40"
          : "border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900/40 dark:hover:bg-slate-800",
        disabled && "cursor-not-allowed opacity-75"
      )}
    >
      <input type="radio" name={group} value={mode} checked={selected} disabled={disabled} onChange={onSelect} className="peer sr-only" />
      <span
        aria-hidden="true"
        className={cn(
          "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2",
          selected ? "border-istara-600 bg-istara-600 text-white dark:border-istara-400" : "border-slate-500 dark:border-slate-400",
          "peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[color:var(--ui-focus)]"
        )}
      >
        {selected && <Check size={13} strokeWidth={3} />}
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-semibold text-slate-950 dark:text-white">{ASSURANCE_MODE_COPY[mode].title}</span>
        <span className="mt-1 block text-xs leading-5 text-slate-600 dark:text-slate-300">{ASSURANCE_MODE_COPY[mode].body}</span>
      </span>
    </label>
  );
}

function LlmJudgeFields({
  policy,
  draft,
  disabled,
  onChange,
}: {
  policy: ProjectDecisionPolicy;
  draft: Draft;
  disabled: boolean;
  onChange: (draft: Draft) => void;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <label className="text-xs font-medium text-slate-700 dark:text-slate-200">
        LLM judge method
        <select
          value={draft.llm_method}
          disabled={disabled}
          onChange={(event) => onChange({ ...draft, llm_method: event.target.value })}
          className="ui-control mt-1 w-full"
        >
          {policy.choices.llm_methods.map((method) => (
            <option key={method} value={method}>
              {LLM_METHOD_LABELS[method] || method}
            </option>
          ))}
        </select>
      </label>
      {draft.llm_method === "full_ensemble" && (
        <label className="text-xs font-medium text-slate-700 dark:text-slate-200">
          Judges in the panel
          <input
            type="number"
            min={policy.choices.llm_judges[0]}
            max={policy.choices.llm_judges[1]}
            value={draft.llm_judges}
            disabled={disabled}
            onChange={(event) => onChange({ ...draft, llm_judges: Number(event.target.value) })}
            className="ui-control mt-1 w-full"
          />
        </label>
      )}
    </div>
  );
}

function EgressConsent({
  endpoint,
  draft,
  disabled,
  onChange,
}: {
  endpoint: Endpoint;
  draft: Draft;
  disabled: boolean;
  onChange: (draft: Draft) => void;
}) {
  const consented = draft.hosted_egress_endpoint_ids.includes(endpoint.endpoint_id);
  const set = (on: boolean) =>
    onChange({
      ...draft,
      hosted_egress_endpoint_ids: toggle(draft.hosted_egress_endpoint_ids, endpoint.endpoint_id, on),
      // Withdrawing consent also stops using the endpoint.
      decider_endpoint_ids: on ? draft.decider_endpoint_ids : toggle(draft.decider_endpoint_ids, endpoint.endpoint_id, false),
    });
  return (
    <label className="mt-2 flex items-start gap-3 rounded-lg bg-sky-50 px-3 py-2 text-xs leading-5 text-sky-900 dark:bg-sky-950/40 dark:text-sky-100">
      <input type="checkbox" checked={consented} disabled={disabled} onChange={(event) => set(event.target.checked)} className="mt-0.5 h-4 w-4" />
      <span>
        <strong>Allow this project to send research excerpts to {endpoint.endpoint_id}.</strong> The excerpt being checked and the
        code&apos;s definition leave this machine for the provider&apos;s servers. Leave this off to keep the project local.
      </span>
    </label>
  );
}

function DeciderItem({
  endpoint,
  draft,
  disabled,
  onChange,
}: {
  endpoint: Endpoint;
  draft: Draft;
  disabled: boolean;
  onChange: (draft: Draft) => void;
}) {
  const hosted = endpoint.locality === "hosted";
  const blocked = hosted && !draft.hosted_egress_endpoint_ids.includes(endpoint.endpoint_id);
  const Icon = hosted ? Cloud : HardDrive;
  return (
    <li className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
      <label className="flex items-start gap-3 text-sm">
        <input
          type="checkbox"
          checked={draft.decider_endpoint_ids.includes(endpoint.endpoint_id)}
          disabled={disabled || blocked}
          onChange={(event) =>
            onChange({ ...draft, decider_endpoint_ids: toggle(draft.decider_endpoint_ids, endpoint.endpoint_id, event.target.checked) })
          }
          className="mt-1 h-4 w-4"
        />
        <span className="min-w-0">
          <span className="flex flex-wrap items-center gap-2 font-semibold text-slate-900 dark:text-white">
            Use {endpoint.endpoint_id}
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 dark:text-slate-400">
              <Icon size={12} aria-hidden="true" />
              {endpoint.locality} · {endpoint.model}
            </span>
          </span>
          {blocked && <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">Allow cloud use below first.</span>}
        </span>
      </label>
      {hosted && <EgressConsent endpoint={endpoint} draft={draft} disabled={disabled} onChange={onChange} />}
    </li>
  );
}

function DeciderChecklist({
  endpoints,
  draft,
  disabled,
  onChange,
}: {
  endpoints: Endpoint[];
  draft: Draft;
  disabled: boolean;
  onChange: (draft: Draft) => void;
}) {
  return (
    <fieldset className="space-y-3">
      <legend className="text-sm font-semibold text-slate-900 dark:text-white">Decision models for this project</legend>
      {endpoints.length === 0 ? (
        <p className="rounded-lg bg-slate-50 px-3 py-3 text-sm text-slate-600 dark:bg-slate-900 dark:text-slate-300">
          No decision models are configured yet. An administrator can add one in Settings, under Decision models.
        </p>
      ) : (
        <ul className="space-y-2">
          {endpoints.map((endpoint) => (
            <DeciderItem key={endpoint.endpoint_id} endpoint={endpoint} draft={draft} disabled={disabled} onChange={onChange} />
          ))}
        </ul>
      )}
    </fieldset>
  );
}

function TrustList({ scopes }: { scopes: TrustScope[] }) {
  if (scopes.length === 0) return null;
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Trust status</h3>
      <ul className="mt-2 space-y-2">
        {scopes.map((scope) => {
          const copy = TRUST_STATUS_COPY[scope.status] || TRUST_STATUS_COPY.shadow;
          return (
            <li key={scope.scope_key} className="flex flex-wrap items-start justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs dark:bg-slate-900">
              <span className="min-w-0 text-slate-700 dark:text-slate-200">
                <strong>{scope.endpoint_id}</strong> · {scope.task_family} · {copy.body}
              </span>
              <span className="flex items-center gap-2">
                {scope.status === "calibrating" && (
                  <span className="tabular-nums text-slate-500 dark:text-slate-400">
                    {Math.min(scope.labelled, TRUST_MIN_LABELS)} of {TRUST_MIN_LABELS} reviewed
                  </span>
                )}
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 font-semibold",
                    scope.status === "trusted"
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-200"
                      : "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                  )}
                >
                  {copy.label}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SaveBar({
  dirty,
  saving,
  saved,
  onSave,
  onDiscard,
}: {
  dirty: boolean;
  saving: boolean;
  saved: boolean;
  onSave: () => void;
  onDiscard: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-slate-200 pt-4 dark:border-slate-700">
      <button type="button" onClick={onSave} disabled={!dirty || saving} className="primary-action disabled:opacity-60">
        {saving && <Loader2 size={14} className="animate-spin" aria-hidden="true" />}
        Save assurance settings
      </button>
      <button type="button" onClick={onDiscard} disabled={!dirty || saving} className="secondary-action disabled:opacity-60">
        Discard changes
      </button>
      {saved && !dirty && (
        <span role="status" className="text-xs font-medium text-emerald-700 dark:text-emerald-300">
          Saved.
        </span>
      )}
    </div>
  );
}

function PolicyEditor({
  titleId,
  policy,
  draft,
  onChange,
}: {
  titleId: string;
  policy: ProjectDecisionPolicy;
  draft: Draft;
  onChange: (draft: Draft) => void;
}) {
  const canEdit = Boolean(policy.can_edit);
  const usesDeciders = USES_DECIDERS.includes(draft.mode);
  const firstActivation = usesDeciders && policy.decider_endpoint_ids.length === 0;
  return (
    <>
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white" id={`${titleId}-mode`}>
          Assurance mode
        </h3>
        {!canEdit && <span className="text-xs font-medium text-slate-500">View only</span>}
      </div>
      <div role="radiogroup" aria-labelledby={`${titleId}-mode`} className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {policy.choices.modes.map((mode) => (
          <ModeCard
            key={mode}
            mode={mode}
            group={`${titleId}-mode`}
            selected={draft.mode === mode}
            disabled={!canEdit}
            onSelect={() => onChange({ ...draft, mode })}
          />
        ))}
      </div>
      {CHOOSES_LLM_METHOD.includes(draft.mode) && <LlmJudgeFields policy={policy} draft={draft} disabled={!canEdit} onChange={onChange} />}
      {usesDeciders && <DeciderChecklist endpoints={policy.available_endpoints} draft={draft} disabled={!canEdit} onChange={onChange} />}
      <details className="rounded-xl border border-slate-200 p-4 dark:border-slate-700" open={firstActivation}>
        <summary className="cursor-pointer text-sm font-semibold text-slate-900 dark:text-white">What is a decision model?</summary>
        <div className="mt-3">
          <DecisionModelExplainer />
        </div>
      </details>
      <TrustList scopes={policy.trust || []} />
    </>
  );
}

function SectionHeader({ titleId }: { titleId: string }) {
  return (
    <div className="border-b border-slate-200 px-5 py-5 dark:border-slate-700 sm:px-6">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-istara-100 text-istara-700 dark:bg-istara-950/60 dark:text-istara-300">
          <ShieldCheck size={20} aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-istara-700 dark:text-istara-300">Assurance</p>
          <h2 id={titleId} className="mt-1 text-xl font-semibold tracking-tight text-slate-950 dark:text-white">
            How outputs are checked before you review them
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Choose which automated reviewers look at this project&apos;s outputs. You still make every final decision, in every mode,
            and the coding reliability gate (three or more independent coders) never changes.
          </p>
        </div>
      </div>
    </div>
  );
}

/** The project's assurance mode, deciders and cloud consent. Renders nothing without a project. */
export default function ProjectAssuranceSection({ projectId }: { projectId: string | null | undefined }) {
  if (!projectId) return null;
  return <ProjectAssurancePanel projectId={projectId} />;
}

function ProjectAssurancePanel({ projectId }: { projectId: string }) {
  const [policy, setPolicy] = useState<ProjectDecisionPolicy | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await decisionModels.projectPolicy(projectId);
      setPolicy(data);
      setDraft(toRequest(data));
    } catch (err) {
      setError(decisionModelErrorMessage(err, "Could not load this project's assurance settings."));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const data = await decisionModels.setProjectPolicy(projectId, draft);
      setPolicy((current) => ({ ...data, trust: current?.trust, can_edit: current?.can_edit }));
      setDraft(toRequest(data));
      setSaved(true);
    } catch (err) {
      setError(decisionModelErrorMessage(err, "Could not save the assurance settings."));
    } finally {
      setSaving(false);
    }
  };

  const titleId = `project-assurance-${projectId}`;
  const dirty = Boolean(policy && draft && JSON.stringify(toRequest(policy)) !== JSON.stringify(draft));

  return (
    <section id="tour-target-project-assurance" className="ui-panel overflow-visible" aria-labelledby={titleId}>
      <SectionHeader titleId={titleId} />
      <div className="space-y-5 px-5 py-5 sm:px-6">
        {loading && (
          <p className="flex items-center gap-2 text-sm text-slate-500" role="status">
            <Loader2 size={15} className="animate-spin" aria-hidden="true" /> Loading assurance settings…
          </p>
        )}
        {error && (
          <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
            {error}
          </p>
        )}
        {policy && draft && <PolicyEditor titleId={titleId} policy={policy} draft={draft} onChange={setDraft} />}
        {policy?.can_edit && draft && (
          <SaveBar dirty={dirty} saving={saving} saved={saved} onSave={() => void save()} onDiscard={() => setDraft(toRequest(policy))} />
        )}
      </div>
    </section>
  );
}
