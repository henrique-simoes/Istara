import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return "\u2014";
  try {
    const d = new Date(date);
    if (isNaN(d.getTime())) return "\u2014";
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  } catch {
    return "\u2014";
  }
}

export function phaseLabel(phase: string): string {
  const labels: Record<string, string> = {
    discover: "💎 Discover",
    define: "💎 Define",
    develop: "💎 Develop",
    deliver: "💎 Deliver",
  };
  return labels[phase] || phase;
}

// W8 UX parity: per-project agent engine indicator/selector.
// null/undefined means "inherit the global default" (legacy until the owner flips it).
const PI_ENGINE_VALUES = new Set(["pi", "pi-candidate", "pi-replacement", "deepseek-pi"]);

export function agentEngineLabel(engine: string | null | undefined): string {
  // CF-SPEC-12: the legacy engine's public UI name is "Istara".
  return engine && PI_ENGINE_VALUES.has(engine.trim().toLowerCase()) ? "Pi" : "Istara";
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    backlog: "Backlog",
    in_progress: "In Progress",
    in_review: "In Review",
    done: "Done",
  };
  return labels[status] || status;
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "text-green-600";
  if (confidence >= 0.5) return "text-yellow-600";
  return "text-red-600";
}
