"use client";

import { cn } from "@/lib/utils";
import type { NotificationCategory } from "@/lib/types";

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

interface CategoryFilterProps {
  selected: string[];
  onChange: (categories: string[]) => void;
}

export default function CategoryFilter({ selected, onChange }: CategoryFilterProps) {
  const toggleCategory = (id: string) => {
    if (selected.includes(id)) {
      onChange(selected.filter((c) => c !== id));
    } else {
      onChange([...selected, id]);
    }
  };

  const selectAll = () => {
    onChange(ALL_CATEGORIES.map((c) => c.id));
  };

  const clearAll = () => {
    onChange([]);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-700 dark:text-slate-300">Categories</span>
        <div className="flex items-center gap-2">
          <button
            onClick={selectAll}
            className="text-[10px] text-reclaw-600 dark:text-reclaw-400 hover:underline"
          >
            Select All
          </button>
          <button
            onClick={clearAll}
            className="text-[10px] text-slate-500 dark:text-slate-400 hover:underline"
          >
            Clear All
          </button>
        </div>
      </div>
      <div className="space-y-1">
        {ALL_CATEGORIES.map((cat) => (
          <label
            key={cat.id}
            className="flex items-center gap-2 py-0.5 cursor-pointer group"
          >
            <input
              type="checkbox"
              checked={selected.includes(cat.id)}
              onChange={() => toggleCategory(cat.id)}
              className="rounded border-slate-300 dark:border-slate-600 text-reclaw-600 focus:ring-reclaw-500 focus:ring-offset-0"
            />
            <span className="text-xs text-slate-600 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-slate-200">
              {cat.label}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

export { ALL_CATEGORIES };
