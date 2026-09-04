"use client";

import { cn } from "@/lib/utils";
import {
  CUSTOM_LOOP_INTERVAL_MAX_SECONDS,
  CUSTOM_LOOP_INTERVAL_MIN_SECONDS,
  customLoopIntervalError,
} from "@/lib/customLoopForm";
import CronBuilder from "./CronBuilder";

export interface CustomLoopForm {
  name: string;
  skill_name: string;
  cron_expression: string;
  interval_seconds: number | "";
  description: string;
  mode: "cron" | "interval";
}

export const EMPTY_CUSTOM_LOOP_FORM: CustomLoopForm = {
  name: "",
  skill_name: "",
  cron_expression: "0 * * * *",
  interval_seconds: 300,
  description: "",
  mode: "interval",
};

type SkillOption = { id: string; name: string };

interface CustomLoopTimingProps {
  form: CustomLoopForm;
  intervalError: string | null;
  onChange: (patch: Partial<CustomLoopForm>) => void;
}

function CustomLoopTiming({ form, intervalError, onChange }: CustomLoopTimingProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-2">Timing Mode</label>
      <div className="flex items-center gap-2 mb-3">
        {(["interval", "cron"] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            onClick={() => onChange({ mode })}
            className={cn(
              "px-3 py-1 text-xs rounded-md border transition-colors",
              form.mode === mode
                ? "bg-istara-100 border-istara-300 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                : "border-slate-200 dark:border-slate-700 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800",
            )}
          >
            {mode === "interval" ? "Fixed Interval" : "Cron Expression"}
          </button>
        ))}
      </div>

      {form.mode === "interval" ? (
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={CUSTOM_LOOP_INTERVAL_MIN_SECONDS}
            max={CUSTOM_LOOP_INTERVAL_MAX_SECONDS}
            value={form.interval_seconds}
            onChange={(event) => onChange({ interval_seconds: parseInt(event.target.value, 10) || "" })}
            aria-invalid={Boolean(intervalError)}
            aria-describedby={intervalError ? "custom-loop-interval-error" : undefined}
            className="w-24 px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
          />
          <span className="text-xs text-slate-500 dark:text-slate-400">seconds</span>
        </div>
      ) : (
        <CronBuilder value={form.cron_expression} onChange={(cron_expression) => onChange({ cron_expression })} />
      )}
      {intervalError && form.mode === "interval" && (
        <p id="custom-loop-interval-error" role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">
          {intervalError}
        </p>
      )}
    </div>
  );
}

interface CustomLoopFormPanelProps {
  form: CustomLoopForm;
  availableSkills: SkillOption[];
  activeProjectId: string | null;
  loading: boolean;
  error: string | null;
  onChange: (form: CustomLoopForm) => void;
  onCreate: () => void;
  onCancel: () => void;
}

export default function CustomLoopFormPanel({
  form,
  availableSkills,
  activeProjectId,
  loading,
  error,
  onChange,
  onCreate,
  onCancel,
}: CustomLoopFormPanelProps) {
  const intervalError = form.mode === "interval" ? customLoopIntervalError(form.interval_seconds) : null;
  const canCreate = Boolean(
    form.name.trim() &&
    form.skill_name.trim() &&
    activeProjectId &&
    (form.mode === "cron" || !intervalError),
  );
  const updateForm = (patch: Partial<CustomLoopForm>) => onChange({ ...form, ...patch });

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Name</label>
          <input
            type="text"
            value={form.name}
            onChange={(event) => updateForm({ name: event.target.value })}
            placeholder="Loop name"
            className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Skill</label>
          <select
            value={form.skill_name}
            onChange={(event) => updateForm({ skill_name: event.target.value })}
            className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
            aria-label="Select skill for this loop"
          >
            <option value="">Select a skill...</option>
            {availableSkills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Description</label>
        <input
          type="text"
          value={form.description}
          onChange={(event) => updateForm({ description: event.target.value })}
          placeholder="Optional description"
          className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
        />
      </div>

      <CustomLoopTiming form={form} intervalError={intervalError} onChange={updateForm} />

      <div className="flex items-center gap-2 pt-2">
        <button
          onClick={onCreate}
          disabled={!canCreate || loading}
          className="px-4 py-1.5 text-sm font-medium rounded-lg bg-istara-600 text-white hover:bg-istara-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Creating..." : "Create Loop"}
        </button>
        {error && <p role="alert" className="text-xs text-red-600 dark:text-red-400">{error}</p>}
        <button
          onClick={onCancel}
          className="px-4 py-1.5 text-sm font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
