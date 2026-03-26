"use client";

import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Clock, Play, Pause } from "lucide-react";
import { useLoopsStore } from "@/stores/loopsStore";
import { cn } from "@/lib/utils";
import CronBuilder from "./CronBuilder";

interface ScheduleForm {
  name: string;
  skill_name: string;
  project_id: string;
  cron_expression: string;
  description: string;
}

const EMPTY_FORM: ScheduleForm = {
  name: "",
  skill_name: "",
  project_id: "",
  cron_expression: "0 * * * *",
  description: "",
};

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const diff = Date.now() - new Date(dateStr).getTime();
  if (diff < 60_000) return "Just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return new Date(dateStr).toLocaleDateString();
}

function formatTimeUntil(dateStr: string | null): string {
  if (!dateStr) return "N/A";
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff < 0) return "Overdue";
  if (diff < 60_000) return "< 1m";
  if (diff < 3_600_000) return `in ${Math.floor(diff / 60_000)}m`;
  return `in ${Math.floor(diff / 3_600_000)}h`;
}

export default function SchedulesTab() {
  const { health, loading, createCustomLoop, fetchHealth } = useLoopsStore();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ScheduleForm>({ ...EMPTY_FORM });
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  // Filter schedules from health (source_type = "schedule" or "custom")
  const schedules = health.filter((h) => h.source_type === "schedule" || h.source_type === "custom");

  const handleCreate = async () => {
    if (!form.name.trim() || !form.skill_name.trim()) return;
    await createCustomLoop({
      name: form.name,
      skill_name: form.skill_name,
      project_id: form.project_id,
      cron_expression: form.cron_expression,
      description: form.description,
    });
    setForm({ ...EMPTY_FORM });
    setShowForm(false);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Cron Schedules</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
            "bg-reclaw-600 text-white hover:bg-reclaw-700"
          )}
        >
          <Plus size={14} />
          Create Schedule
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
                placeholder="e.g. Daily UX Scan"
                className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Skill Name</label>
              <input
                type="text"
                value={form.skill_name}
                onChange={(e) => setForm({ ...form, skill_name: e.target.value })}
                placeholder="e.g. ux_evaluation"
                className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Description</label>
            <input
              type="text"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Optional description..."
              className="w-full px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-2">Cron Expression</label>
            <CronBuilder value={form.cron_expression} onChange={(cron) => setForm({ ...form, cron_expression: cron })} />
          </div>
          <div className="flex items-center gap-2 pt-2">
            <button
              onClick={handleCreate}
              disabled={!form.name.trim() || !form.skill_name.trim()}
              className="px-4 py-1.5 text-sm font-medium rounded-lg bg-reclaw-600 text-white hover:bg-reclaw-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Create
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

      {/* Schedule list */}
      {schedules.length === 0 && !loading ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400 dark:text-slate-500">
          <Clock size={40} className="mb-3 opacity-50" />
          <p className="text-sm">No cron schedules yet.</p>
          <p className="text-xs mt-1">Click &ldquo;Create Schedule&rdquo; to add one.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {schedules.map((schedule) => (
            <div
              key={`${schedule.source_type}-${schedule.source_id}`}
              className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <span className={cn(
                    "w-2 h-2 rounded-full shrink-0",
                    schedule.status === "active" ? "bg-green-500" :
                    schedule.status === "paused" ? "bg-yellow-500" : "bg-red-500"
                  )} />
                  <div className="min-w-0">
                    <h3 className="text-sm font-medium text-slate-900 dark:text-white truncate">
                      {schedule.source_name}
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      Interval: {schedule.interval_seconds}s
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                  <span>Last: {formatTimeAgo(schedule.last_execution_at)}</span>
                  <span>Next: {formatTimeUntil(schedule.next_expected_at)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
