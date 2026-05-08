import { User } from "lucide-react";

import type { ThinkingMode } from "@/lib/types";

export function UserAvatar() {
  return (
    <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center flex-shrink-0">
      <User size={16} className="text-slate-500 dark:text-slate-400" />
    </div>
  );
}

export function AgentAvatar({ name }: { name?: string }) {
  const label = name || "Istara";
  return (
    <div
      className="w-8 h-8 rounded-full bg-istara-100 dark:bg-istara-900/40 flex items-center justify-center flex-shrink-0"
      title={label}
    >
      <span className="text-sm">🐾</span>
    </div>
  );
}

export const PRESET_INFO: Record<string, { icon: string; label: string; desc: string }> = {
  lightweight: { icon: "⚡", label: "Lightweight", desc: "Fast, minimal reasoning. Quick questions." },
  medium: { icon: "⚖️", label: "Medium", desc: "Balanced speed and depth. Most tasks." },
  high: { icon: "🧠", label: "High", desc: "Deep reasoning, large context. Complex analysis." },
  custom: { icon: "🔧", label: "Custom", desc: "Your own temperature, tokens, context." },
};

export const REASONING_PRESETS: Record<string, { temperature: number; maxTokens: number; topP: number }> = {
  quick: { temperature: 0.3, maxTokens: 1024, topP: 0.8 },
  balanced: { temperature: 0.7, maxTokens: 2048, topP: 0.9 },
  deep: { temperature: 0.9, maxTokens: 4096, topP: 0.95 },
};

export const THINKING_INFO: Record<ThinkingMode, { label: string; desc: string }> = {
  server_default: { label: "Default", desc: "Use the LLM server setting." },
  off: { label: "Off", desc: "Ask for direct answers only." },
  auto: { label: "Auto", desc: "Let Istara adapt to the model." },
  on: { label: "On", desc: "Ask for private reasoning when supported." },
};
