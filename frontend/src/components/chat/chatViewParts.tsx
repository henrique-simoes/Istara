import { User } from "lucide-react";

export function UserAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 dark:bg-slate-700">
      <User size={16} className="text-slate-500 dark:text-slate-400" aria-hidden="true" />
    </div>
  );
}

export function AgentAvatar({ name }: { name?: string }) {
  const label = name || "Istara";
  return (
    <div
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-istara-100 dark:bg-istara-900/40"
      title={label}
      aria-label={label}
    >
      <span className="text-sm" aria-hidden="true">🐾</span>
    </div>
  );
}
