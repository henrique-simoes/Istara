"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Power, PowerOff, RefreshCw } from "lucide-react";
import { useLoopsStore } from "@/stores/loopsStore";
import { useProjectStore } from "@/stores/projectStore";
import { skills as skillsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import CronBuilder from "./CronBuilder";

interface CustomLoopForm {
  name: string;
  skill_name: string;
  project_id: string;
  cron_expression: string;
  interval_seconds: number | "";
  description: string;
  mode: "cron" | "interval";
}

const EMPTY_FORM: CustomLoopForm = {
  name: "",
  skill_name: "",
  project_id: "",
  cron_expression: "0 * * * *",
  interval_seconds: 60,
  description: "",
  mode: "interval",
};

export default function CustomLoopsTab() {
  const { health, loading, createCustomLoop, fetchHealth } = useLoopsStore();
  const { projects, fetchProjects } = useProjectStore();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CustomLoopForm>({ ...EMPTY_FORM });
  const [availableSkills, setAvailableSkills] = useState<{ id: string; name: string }[]>([]);

  useEffect(() => {
    fetchHealth();
    fetchProjects();
    // Load available skills for the dropdown
    skillsApi.list().then((res: any) => {
      const list = Array.isArray(res) ? res : (res?.skills ?? []);
      setAvailableSkills(list.map((s: any) => ({ id: s.skill_id || s.id, name: s.name || s.skill_id || s.id })));
    }).catch(() => {});
  }, [fetchHealth, fetchProjects]);

  const customLoops = health.filter((h) => h.source_type === "custom");

  const handleCreate = async () => {
    if (!form.name.trim() || !form.skill_name.trim()) return;
    const data: Parameters<typeof createCustomLoop>[0] = {
      name: form.name,
      skill_name: form.skill_name,
      project_id: form.project_id,
      description: form.description,
    };
    if (form.mode === "cron") {
      data.cron_expression = form.cron_expression;
    } else {
      data.interval_seconds = typeof form.interval_seconds === "number" ? form.interval_seconds : 60;
    }
    await createCustomLoop(data);
    setForm({ ...EMPTY_FORM });
    setShowForm(false);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Custom Loops</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-reclaw-600 text-white hover:bg-reclaw-700 transition-colors"
        >
          <Plus size={14} />
          Create Loop
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Loop name"
                className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Skill</label>
              <select
                value={form.skill_name}
                onChange={(e) => setForm({ ...form, skill_name: e.target.value })}
                className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                aria-label="Select skill for this loop"
              >
                <option value="">Select a skill...</option>
                {availableSkills.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Project</label>
              <select
                value={form.project_id}
                onChange={(e) => setForm({ ...form, project_id: e.target.value })}
                className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              >
                <option value="">All projects</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Description</label>
              <input
                type="text"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Optional description"
                className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              />
            </div>
          </div>

          {/* Mode toggle */}
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-2">Timing Mode</label>
            <div className="flex items-center gap-2 mb-3">
              <button
                type="button"
                onClick={() => setForm({ ...form, mode: "interval" })}
                className={cn(
                  "px-3 py-1 text-xs rounded-md border transition-colors",
                  form.mode === "interval"
                    ? "bg-reclaw-100 border-reclaw-300 text-reclaw-700 dark:bg-reclaw-900/30 dark:text-reclaw-400"
                    : "border-slate-200 dark:border-slate-700 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800"
                )}
              >
                Fixed Interval
              </button>
              <button
                type="button"
                onClick={() => setForm({ ...form, mode: "cron" })}
                className={cn(
                  "px-3 py-1 text-xs rounded-md border transition-colors",
                  form.mode === "cron"
                    ? "bg-reclaw-100 border-reclaw-300 text-reclaw-700 dark:bg-reclaw-900/30 dark:text-reclaw-400"
                    : "border-slate-200 dark:border-slate-700 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800"
                )}
              >
                Cron Expression
              </button>
            </div>

            {form.mode === "interval" ? (
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={10}
                  max={86400}
                  value={form.interval_seconds}
                  onChange={(e) => setForm({ ...form, interval_seconds: parseInt(e.target.value, 10) || "" })}
                  className="w-24 px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                />
                <span className="text-xs text-slate-500 dark:text-slate-400">seconds</span>
              </div>
            ) : (
              <CronBuilder value={form.cron_expression} onChange={(cron) => setForm({ ...form, cron_expression: cron })} />
            )}
          </div>

          <div className="flex items-center gap-2 pt-2">
            <button
              onClick={handleCreate}
              disabled={!form.name.trim() || !form.skill_name.trim() || loading}
              className="px-4 py-1.5 text-sm font-medium rounded-lg bg-reclaw-600 text-white hover:bg-reclaw-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Creating..." : "Create Loop"}
            </button>
            <button
              onClick={() => { setShowForm(false); setForm({ ...EMPTY_FORM }); }}
              className="px-4 py-1.5 text-sm font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Custom loops list */}
      {customLoops.length === 0 && !loading ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400 dark:text-slate-500">
          <RefreshCw size={40} className="mb-3 opacity-50" />
          <p className="text-sm">No custom loops yet.</p>
          <p className="text-xs mt-1">Create a custom loop to run skills on a schedule.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {customLoops.map((loop) => (
            <div
              key={`${loop.source_type}-${loop.source_id}`}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <span className={cn(
                    "w-2 h-2 rounded-full shrink-0",
                    loop.status === "active" ? "bg-green-500" :
                    loop.status === "paused" ? "bg-yellow-500" : "bg-red-500"
                  )} />
                  <div className="min-w-0">
                    <h3 className="text-sm font-medium text-slate-900 dark:text-white truncate">
                      {loop.source_name}
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      {loop.interval_seconds}s interval
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full",
                    loop.status === "active"
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                  )}>
                    {loop.status}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
