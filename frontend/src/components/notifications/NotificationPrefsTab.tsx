"use client";

import { useEffect, useState } from "react";
import { Save, Settings2 } from "lucide-react";
import { useNotificationStore } from "@/stores/notificationStore";
import { cn } from "@/lib/utils";
import type { NotificationCategory, NotificationPreference } from "@/lib/types";

const ALL_CATEGORIES: { id: NotificationCategory; label: string }[] = [
  { id: "agent_status", label: "Agent Status" },
  { id: "task_progress", label: "Task Progress" },
  { id: "finding_created", label: "Finding Created" },
  { id: "file_processed", label: "File Processed" },
  { id: "suggestion", label: "Suggestions" },
  { id: "resource_throttle", label: "Resource Throttle" },
  { id: "scheduled_reminder", label: "Scheduled Reminder" },
  { id: "document", label: "Documents" },
  { id: "loop_execution", label: "Loop Execution" },
  { id: "system", label: "System" },
];

interface PrefRow {
  category: NotificationCategory;
  show_toast: boolean;
  show_center: boolean;
  email_forward: boolean;
}

export default function NotificationPrefsTab() {
  const { preferences, fetchPreferences, updatePreferences, loading } = useNotificationStore();
  const [rows, setRows] = useState<PrefRow[]>([]);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    fetchPreferences();
  }, [fetchPreferences]);

  // Initialize rows from preferences or defaults
  useEffect(() => {
    const prefMap = new Map(
      preferences.map((p) => [p.category, p])
    );

    const newRows = ALL_CATEGORIES.map((cat) => {
      const existing = prefMap.get(cat.id);
      return {
        category: cat.id,
        show_toast: existing?.show_toast ?? true,
        show_center: existing?.show_center ?? true,
        email_forward: existing?.email_forward ?? false,
      };
    });
    setRows(newRows);
    setDirty(false);
  }, [preferences]);

  const toggleField = (index: number, field: keyof PrefRow) => {
    setRows((prev) => {
      const updated = [...prev];
      (updated[index] as any)[field] = !(updated[index] as any)[field];
      return updated;
    });
    setDirty(true);
  };

  const handleSave = async () => {
    const prefs: NotificationPreference[] = rows.map((row) => ({
      id: `pref-${row.category}`,
      category: row.category,
      agent_id: null,
      show_toast: row.show_toast,
      show_center: row.show_center,
      email_forward: row.email_forward,
    }));
    await updatePreferences(prefs);
    setDirty(false);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Notification Preferences</h2>
      </div>

      <p className="text-sm text-slate-500 dark:text-slate-400">
        Control how you receive notifications for each category.
      </p>

      {/* Preferences table */}
      <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
              <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 dark:text-slate-400">Category</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-slate-500 dark:text-slate-400">Show Toast</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-slate-500 dark:text-slate-400">Show in Center</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-slate-500 dark:text-slate-400">Email Forward</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const catInfo = ALL_CATEGORIES.find((c) => c.id === row.category);
              return (
                <tr
                  key={row.category}
                  className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                >
                  <td className="px-4 py-3 text-sm font-medium text-slate-900 dark:text-white">
                    {catInfo?.label || row.category}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <ToggleSwitch
                      checked={row.show_toast}
                      onChange={() => toggleField(index, "show_toast")}
                      label={`Toggle toast for ${catInfo?.label}`}
                    />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <ToggleSwitch
                      checked={row.show_center}
                      onChange={() => toggleField(index, "show_center")}
                      label={`Toggle center for ${catInfo?.label}`}
                    />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <ToggleSwitch
                      checked={row.email_forward}
                      onChange={() => toggleField(index, "email_forward")}
                      label={`Toggle email for ${catInfo?.label}`}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Save button */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={!dirty || loading}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
            dirty
              ? "bg-istara-600 text-white hover:bg-istara-700"
              : "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
          )}
        >
          <Save size={14} />
          {loading ? "Saving..." : "Save Preferences"}
        </button>
        {dirty && (
          <span className="text-xs text-amber-600 dark:text-amber-400">Unsaved changes</span>
        )}
      </div>
    </div>
  );
}

function ToggleSwitch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={onChange}
      className={cn(
        "relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-istara-500 focus:ring-offset-2 dark:focus:ring-offset-slate-900",
        checked ? "bg-istara-600" : "bg-slate-300 dark:bg-slate-600"
      )}
    >
      <span
        className={cn(
          "inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform",
          checked ? "translate-x-4" : "translate-x-0.5"
        )}
      />
    </button>
  );
}
