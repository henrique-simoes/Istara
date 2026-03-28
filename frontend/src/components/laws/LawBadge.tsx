"use client";

import { cn } from "@/lib/utils";

const CATEGORY_COLORS: Record<string, string> = {
  perception: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  cognitive: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  behavioral: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  principles: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
};

interface LawBadgeProps {
  lawId: string;
  lawName?: string;
  category?: string;
  onClick?: () => void;
}

export default function LawBadge({ lawId, lawName, category, onClick }: LawBadgeProps) {
  const colorClass = CATEGORY_COLORS[category || ""] || "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400";
  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium transition-colors",
        colorClass,
        onClick && "cursor-pointer hover:opacity-80"
      )}
      aria-label={`UX Law: ${lawName || lawId}`}
    >
      {lawName || lawId.replace(/-/g, " ")}
    </button>
  );
}
