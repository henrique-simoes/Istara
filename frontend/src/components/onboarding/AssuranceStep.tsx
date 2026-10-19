"use client";

import { ArrowLeft, Sparkles } from "lucide-react";
import type { AssuranceMode } from "@/lib/catalogTypes";
import { ASSURANCE_MODE_COPY, DECISION_MODEL_EXPLAINER } from "@/lib/decisionModelCopy";

const ONBOARDING_MODES: AssuranceMode[] = ["llm_judges", "decision_models", "both", "none"];

/** Onboarding: how outputs are checked, and what a decision model is. Informational; enables
 * nothing (owner decision DEC-1: no decision model by default). */
export default function AssuranceStep({
  hasUploads,
  onBack,
  onFinish,
}: {
  hasUploads: boolean;
  onBack: () => void;
  onFinish: () => void;
}) {
  return (
    <div>
      <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-1">How outputs are checked</h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
        Before an output reaches you, automated reviewers can check it. You always make the final decision. Each project chooses
        its reviewers in Project Settings, under Assurance.
      </p>
      <ul className="mb-4 space-y-2">
        {ONBOARDING_MODES.map((mode) => (
          <li key={mode} className="rounded-lg bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs leading-5 text-slate-600 dark:text-slate-300">
            <strong className="text-slate-900 dark:text-white">{ASSURANCE_MODE_COPY[mode].title}.</strong> {ASSURANCE_MODE_COPY[mode].body}
          </li>
        ))}
      </ul>
      <details className="mb-6 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2">
        <summary className="cursor-pointer text-sm font-medium text-slate-900 dark:text-white">{DECISION_MODEL_EXPLAINER.title}</summary>
        <p className="mt-2 text-xs leading-5 text-slate-600 dark:text-slate-300">{DECISION_MODEL_EXPLAINER.lead}</p>
        <ul className="mt-2 space-y-1">
          {DECISION_MODEL_EXPLAINER.principles.map((principle) => (
            <li key={principle.title} className="text-xs leading-5 text-slate-600 dark:text-slate-300">
              <strong className="text-slate-900 dark:text-white">{principle.title}.</strong> {principle.body}
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">
          None is turned on. An administrator can add one later in Settings, under Decision models.
        </p>
      </details>
      <div className="flex justify-between">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-400 hover:text-slate-600">
          <ArrowLeft size={14} /> Back
        </button>
        <button
          onClick={onFinish}
          className="flex items-center gap-2 px-5 py-2.5 bg-istara-600 text-white rounded-xl hover:bg-istara-700 font-medium text-sm"
        >
          {hasUploads ? "Start Researching" : "Skip & Explore"} <Sparkles size={14} />
        </button>
      </div>
    </div>
  );
}
