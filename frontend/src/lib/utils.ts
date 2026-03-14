import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
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
