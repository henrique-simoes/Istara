"use client";

import { useEffect, useState } from "react";
import { Loader2, Scale } from "lucide-react";
import { validation } from "@/lib/api";
import type { DecisionModelHealth } from "@/lib/catalogTypes";
import { TRUST_STATUS_COPY } from "@/lib/decisionModelCopy";
import { cn } from "@/lib/utils";

const fmt = (value: number | null | undefined, digits = 2) =>
  value === null || value === undefined || Number.isNaN(value) ? "—" : value.toFixed(digits);

const pct = (value: number | null | undefined) =>
  value === null || value === undefined ? "—" : `${Math.round(value * 100)}%`;

type Health = DecisionModelHealth;

function isEmpty(data: Health | null): boolean {
  return !data || (data.scopes.length === 0 && data.llm_methods.length === 0 && !data.error_structure?.labelled_items);
}

function scopeStatus(scope: Health["scopes"][number]): "trusted" | "calibrating" | "shadow" {
  if (scope.trusted) return "trusted";
  return scope.reasons.includes("not_evaluated") ? "calibrating" : "shadow";
}

function ScopeTable({ scopes }: { scopes: Health["scopes"] }) {
  if (scopes.length === 0) return null;
  return (
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-xs">
          <caption className="sr-only">Decision-model trust by scope</caption>
          <thead className="text-slate-500 dark:text-slate-400">
            <tr>
              <th scope="col" className="py-1.5 pr-3 font-medium">Decision model</th>
              <th scope="col" className="py-1.5 pr-3 font-medium">Status</th>
              <th scope="col" className="py-1.5 pr-3 font-medium tabular-nums">Reviewed</th>
              <th scope="col" className="py-1.5 pr-3 font-medium">Calibration error (ECE)</th>
              <th scope="col" className="py-1.5 pr-3 font-medium">Brier</th>
              <th scope="col" className="py-1.5 font-medium">Agreement (κ)</th>
            </tr>
          </thead>
          <tbody className="text-slate-700 dark:text-slate-200">
            {scopes.map((scope) => {
              const status = scopeStatus(scope);
              return (
                <tr key={scope.scope_key} className="border-t border-slate-100 dark:border-slate-700">
                  <td className="py-1.5 pr-3">
                    <span className="font-medium">{scope.endpoint_id}</span>
                    <span className="block text-[11px] text-slate-500 dark:text-slate-400">{scope.task_family}</span>
                  </td>
                  <td className="py-1.5 pr-3">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[11px] font-semibold",
                        status === "trusted"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-200"
                          : "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200"
                      )}
                      title={TRUST_STATUS_COPY[status].body}
                    >
                      {TRUST_STATUS_COPY[status].label}
                    </span>
                  </td>
                  <td className="py-1.5 pr-3 tabular-nums">{scope.labelled} / {scope.verdicts}</td>
                  <td className="py-1.5 pr-3 tabular-nums">{fmt(scope.metrics.held_out_ece, 3)}</td>
                  <td className="py-1.5 pr-3 tabular-nums">{fmt(scope.metrics.held_out_brier, 3)}</td>
                  <td className="py-1.5 tabular-nums">{fmt(scope.metrics.kappa)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
  );
}

function LlmMethodList({ methods }: { methods: Health["llm_methods"] }) {
  if (methods.length === 0) return null;
  return (
      <div>
        <h4 className="text-xs font-semibold text-slate-700 dark:text-slate-200">LLM judge methods: agreement with your decisions</h4>
        <ul className="mt-2 grid gap-2 sm:grid-cols-2">
          {methods.map((method) => (
            <li key={method.method} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-xs dark:bg-slate-900">
              <span className="text-slate-700 dark:text-slate-200">{method.method}</span>
              <span className="tabular-nums text-slate-900 dark:text-white">
                {pct(method.human_accuracy)}{" "}
                <span className="text-slate-500 dark:text-slate-400">
                  ({method.human_agree} of {method.human_agree + method.human_disagree})
                </span>
              </span>
            </li>
          ))}
        </ul>
      </div>
  );
}

function ErrorStructure({ structure }: { structure: Health["error_structure"] | undefined }) {
  if (!structure || structure.evaluators.length < 2) return null;
  return (
      <div>
        <h4 className="text-xs font-semibold text-slate-700 dark:text-slate-200">
          Do the evaluators fail together? ({structure.labelled_items} reviewed items)
        </h4>
        <dl className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="rounded-md bg-slate-50 px-3 py-2 dark:bg-slate-900">
            <dt className="text-[11px] text-slate-500 dark:text-slate-400">Evaluators</dt>
            <dd className="font-mono text-sm font-semibold tabular-nums text-slate-900 dark:text-white">{structure.evaluators.length}</dd>
          </div>
          <div className="rounded-md bg-slate-50 px-3 py-2 dark:bg-slate-900">
            <dt className="text-[11px] text-slate-500 dark:text-slate-400">Effectively independent</dt>
            <dd className="font-mono text-sm font-semibold tabular-nums text-slate-900 dark:text-white">{fmt(structure.effective_evaluators, 1)}</dd>
          </div>
          <div className="rounded-md bg-slate-50 px-3 py-2 dark:bg-slate-900">
            <dt className="text-[11px] text-slate-500 dark:text-slate-400">Mean error correlation</dt>
            <dd className="font-mono text-sm font-semibold tabular-nums text-slate-900 dark:text-white">{fmt(structure.mean_error_correlation)}</dd>
          </div>
          <div className="rounded-md bg-slate-50 px-3 py-2 dark:bg-slate-900">
            <dt className="text-[11px] text-slate-500 dark:text-slate-400">Panel reliability model</dt>
            <dd className="text-xs font-semibold text-slate-900 dark:text-white">
              {structure.dawid_skene ? (structure.dawid_skene.converged ? "Dawid–Skene fitted" : "Did not converge") : "Needs 3+ evaluators"}
            </dd>
          </div>
        </dl>
        {structure.pairs.length > 0 && (
          <ul className="mt-2 space-y-1 text-[11px] text-slate-600 dark:text-slate-300">
            {structure.pairs.map((pair) => (
              <li key={`${pair.a}-${pair.b}`} className="tabular-nums">
                {pair.a} × {pair.b}: error correlation {fmt(pair.error_correlation)}, Yule&apos;s Q {fmt(pair.yules_q)} on {pair.n} items
              </li>
            ))}
          </ul>
        )}
        {structure.dawid_skene?.note && (
          <p className="mt-2 text-[11px] leading-5 text-slate-500 dark:text-slate-400">{structure.dawid_skene.note}</p>
        )}
      </div>
  );
}

// Decision models and LLM judges on one error model, against human review (CF-SPEC-1, Phase 5).
export default function DecisionModelHealthPanel({ projectId }: { projectId: string }) {
  const [data, setData] = useState<DecisionModelHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    validation
      .decisionModels(projectId)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch(() => {
        if (!cancelled) setError("Decision-model health is unavailable right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const empty = Boolean(data) && isEmpty(data);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800" aria-labelledby="decision-model-health-title">
      <div className="flex items-start gap-3">
        <Scale size={18} className="mt-0.5 text-slate-500 dark:text-slate-400" aria-hidden="true" />
        <div className="min-w-0">
          <h3 id="decision-model-health-title" className="text-sm font-semibold text-slate-900 dark:text-white">
            Evaluator health against your reviews
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
            Decision models and LLM judges are measured on the same items you reviewed. Evaluators that make the same mistakes add
            little: the effective number of independent evaluators shows how much the panel really checks.
          </p>
        </div>
      </div>

      {loading && (
        <p role="status" className="mt-4 flex items-center gap-2 text-xs text-slate-500">
          <Loader2 size={14} className="animate-spin" aria-hidden="true" /> Loading evaluator health…
        </p>
      )}
      {error && (
        <p role="status" className="mt-4 text-xs text-amber-700 dark:text-amber-300">
          {error}
        </p>
      )}
      {empty && (
        <p className="mt-4 rounded-lg bg-slate-50 px-3 py-3 text-xs text-slate-600 dark:bg-slate-900 dark:text-slate-300">
          Nothing to measure yet. Figures appear after automated reviewers have run and you have reviewed their items.
        </p>
      )}

      {data && !empty && (
        <div className="mt-4 space-y-4">
          <ScopeTable scopes={data.scopes} />
          <LlmMethodList methods={data.llm_methods} />
          <ErrorStructure structure={data.error_structure} />
        </div>
      )}
    </section>
  );
}
