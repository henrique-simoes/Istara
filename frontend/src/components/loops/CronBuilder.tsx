"use client";

import { useState, useEffect, useMemo } from "react";
import { cn } from "@/lib/utils";

interface CronBuilderProps {
  value: string;
  onChange: (cron: string) => void;
}

const PRESETS: { label: string; cron: string }[] = [
  { label: "Every minute", cron: "* * * * *" },
  { label: "Every 5 min", cron: "*/5 * * * *" },
  { label: "Every hour", cron: "0 * * * *" },
  { label: "Daily at 9am", cron: "0 9 * * *" },
  { label: "Weekdays at 9am", cron: "0 9 * * 1-5" },
  { label: "Every Monday", cron: "0 9 * * 1" },
];

const MINUTE_OPTIONS = [{ label: "Every", value: "*" }, ...Array.from({ length: 60 }, (_, i) => ({ label: String(i), value: String(i) }))];
const HOUR_OPTIONS = [{ label: "Every", value: "*" }, ...Array.from({ length: 24 }, (_, i) => ({ label: String(i), value: String(i) }))];
const DOM_OPTIONS = [{ label: "Every", value: "*" }, ...Array.from({ length: 31 }, (_, i) => ({ label: String(i + 1), value: String(i + 1) }))];
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_OPTIONS = [{ label: "Every", value: "*" }, ...MONTH_NAMES.map((name, i) => ({ label: name, value: String(i + 1) }))];
const DOW_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const DOW_OPTIONS = [{ label: "Every", value: "*" }, ...DOW_NAMES.map((name, i) => ({ label: name, value: String(i) }))];

function parseCron(cron: string): string[] {
  const parts = cron.trim().split(/\s+/);
  while (parts.length < 5) parts.push("*");
  return parts.slice(0, 5);
}

function describeNextRuns(cron: string, count = 5): string[] {
  // Simple next-run estimation for common patterns
  try {
    const parts = parseCron(cron);
    const results: string[] = [];
    const now = new Date();
    let cursor = new Date(now);

    for (let attempts = 0; attempts < 1000 && results.length < count; attempts++) {
      cursor = new Date(cursor.getTime() + 60_000); // advance by 1 minute

      const minute = cursor.getMinutes();
      const hour = cursor.getHours();
      const dom = cursor.getDate();
      const month = cursor.getMonth() + 1;
      const dow = cursor.getDay();

      if (!matchField(parts[0], minute)) continue;
      if (!matchField(parts[1], hour)) continue;
      if (!matchField(parts[2], dom)) continue;
      if (!matchField(parts[3], month)) continue;
      if (!matchField(parts[4], dow)) continue;

      results.push(cursor.toLocaleString("en-US", {
        weekday: "short", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit",
      }));
    }
    return results.length > 0 ? results : ["Unable to compute next runs"];
  } catch {
    return ["Invalid cron expression"];
  }
}

function matchField(field: string, value: number): boolean {
  if (field === "*") return true;
  // Handle step values like */5
  if (field.startsWith("*/")) {
    const step = parseInt(field.slice(2), 10);
    return step > 0 && value % step === 0;
  }
  // Handle ranges like 1-5
  if (field.includes("-")) {
    const [min, max] = field.split("-").map(Number);
    return value >= min && value <= max;
  }
  // Handle lists like 1,3,5
  if (field.includes(",")) {
    return field.split(",").map(Number).includes(value);
  }
  return parseInt(field, 10) === value;
}

function humanReadable(cron: string): string {
  const parts = parseCron(cron);
  const [min, hr, dom, mon, dow] = parts;

  if (cron === "* * * * *") return "Every minute";
  if (min.startsWith("*/") && hr === "*" && dom === "*" && mon === "*" && dow === "*")
    return `Every ${min.slice(2)} minutes`;
  if (hr === "*" && min !== "*" && dom === "*" && mon === "*" && dow === "*")
    return `Every hour at minute ${min}`;
  if (dom === "*" && mon === "*" && dow === "*" && hr !== "*" && min !== "*")
    return `Daily at ${hr}:${min.padStart(2, "0")}`;
  if (dow === "1-5" && hr !== "*" && min !== "*")
    return `Weekdays at ${hr}:${min.padStart(2, "0")}`;
  if (dow !== "*" && hr !== "*" && min !== "*") {
    const dayName = DOW_NAMES[parseInt(dow, 10)] || dow;
    return `Every ${dayName} at ${hr}:${min.padStart(2, "0")}`;
  }
  return cron;
}

export default function CronBuilder({ value, onChange }: CronBuilderProps) {
  const parts = useMemo(() => parseCron(value), [value]);
  const [minute, setMinute] = useState(parts[0]);
  const [hour, setHour] = useState(parts[1]);
  const [dom, setDom] = useState(parts[2]);
  const [month, setMonth] = useState(parts[3]);
  const [dow, setDow] = useState(parts[4]);

  useEffect(() => {
    const p = parseCron(value);
    setMinute(p[0]);
    setHour(p[1]);
    setDom(p[2]);
    setMonth(p[3]);
    setDow(p[4]);
  }, [value]);

  const updateField = (index: number, val: string) => {
    const newParts = [minute, hour, dom, month, dow];
    newParts[index] = val;
    const setters = [setMinute, setHour, setDom, setMonth, setDow];
    setters[index](val);
    onChange(newParts.join(" "));
  };

  const cronStr = `${minute} ${hour} ${dom} ${month} ${dow}`;
  const nextRuns = useMemo(() => describeNextRuns(cronStr), [cronStr]);

  const fields = [
    { label: "Minute", options: MINUTE_OPTIONS, value: minute, index: 0 },
    { label: "Hour", options: HOUR_OPTIONS, value: hour, index: 1 },
    { label: "Day of Month", options: DOM_OPTIONS, value: dom, index: 2 },
    { label: "Month", options: MONTH_OPTIONS, value: month, index: 3 },
    { label: "Day of Week", options: DOW_OPTIONS, value: dow, index: 4 },
  ];

  return (
    <div className="space-y-3">
      {/* Preset buttons */}
      <div className="flex flex-wrap gap-1.5">
        {PRESETS.map((preset) => (
          <button
            key={preset.cron}
            type="button"
            onClick={() => onChange(preset.cron)}
            className={cn(
              "text-xs px-2.5 py-1 rounded-md border transition-colors",
              value === preset.cron
                ? "bg-reclaw-100 border-reclaw-300 text-reclaw-700 dark:bg-reclaw-900/30 dark:border-reclaw-600 dark:text-reclaw-400"
                : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
            )}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Field dropdowns */}
      <div className="grid grid-cols-5 gap-2">
        {fields.map((field) => (
          <div key={field.label}>
            <label className="block text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
              {field.label}
            </label>
            <select
              value={field.value}
              onChange={(e) => updateField(field.index, e.target.value)}
              className="w-full text-xs px-2 py-1.5 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-reclaw-500"
            >
              {field.options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      {/* Live preview */}
      <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
            Expression: <code className="ml-1 px-1.5 py-0.5 bg-slate-200 dark:bg-slate-700 rounded text-[11px]">{cronStr}</code>
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {humanReadable(cronStr)}
          </span>
        </div>
        <div className="text-[11px] text-slate-500 dark:text-slate-400">
          <p className="font-medium mb-1">Next 5 runs:</p>
          <ul className="space-y-0.5">
            {nextRuns.map((run, i) => (
              <li key={i}>{run}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
