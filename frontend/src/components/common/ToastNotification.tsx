"use client";

import { useEffect, useState, useCallback } from "react";
import {
  CheckCircle,
  AlertTriangle,
  Info,
  X,
  FileText,
  Lightbulb,
  Cpu,
} from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { cn } from "@/lib/utils";
import type { WSEvent } from "@/lib/types";

interface Toast {
  id: string;
  type: "success" | "warning" | "info" | "agent" | "file" | "suggestion";
  title: string;
  message: string;
  timestamp: number;
  duration: number; // ms, 0 = sticky
  actions?: { label: string; onClick: () => void }[];
  navigateTo?: string; // view name to navigate to on click
}

const ICONS = {
  success: CheckCircle,
  warning: AlertTriangle,
  info: Info,
  agent: Cpu,
  file: FileText,
  suggestion: Lightbulb,
};

const COLORS = {
  success: "border-green-500 bg-green-50 dark:bg-green-900/20",
  warning: "border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20",
  info: "border-blue-500 bg-blue-50 dark:bg-blue-900/20",
  agent: "border-reclaw-500 bg-reclaw-50 dark:bg-reclaw-900/20",
  file: "border-purple-500 bg-purple-50 dark:bg-purple-900/20",
  suggestion: "border-amber-500 bg-amber-50 dark:bg-amber-900/20",
};

const ICON_COLORS = {
  success: "text-green-600",
  warning: "text-yellow-600",
  info: "text-blue-600",
  agent: "text-reclaw-600",
  file: "text-purple-600",
  suggestion: "text-amber-600",
};

let nextId = 0;

export default function ToastNotification() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback(
    (type: Toast["type"], title: string, message: string, duration = 5000, navigateTo?: string) => {
      const toast: Toast = {
        id: `toast-${nextId++}`,
        type,
        title,
        message,
        timestamp: Date.now(),
        duration,
        navigateTo,
      };
      setToasts((prev) => [...prev.slice(-4), toast]); // Max 5 visible
    },
    []
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Auto-dismiss toasts
  useEffect(() => {
    const interval = setInterval(() => {
      setToasts((prev) =>
        prev.filter((t) => t.duration === 0 || Date.now() - t.timestamp < t.duration)
      );
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Listen for WebSocket events and create toasts
  const handleEvent = useCallback(
    (event: WSEvent) => {
      switch (event.type) {
        case "agent_status": {
          const status = event.data.status as string;
          const details = event.data.details as string;
          if (status === "working") {
            addToast("agent", "🤖 Agent Working", details, 8000, "agents");
          } else if (status === "error") {
            addToast("warning", "⚠️ Agent Error", details, 10000, "agents");
          }
          break;
        }
        case "task_progress": {
          const progress = Math.round(((event.data.progress as number) || 0) * 100);
          const notes = (event.data.notes as string) || "";
          if (progress === 100) {
            addToast("success", "✅ Task Complete", notes, 5000, "tasks");
          }
          break;
        }
        case "file_processed": {
          const filename = event.data.filename as string;
          const chunks = event.data.chunks as number;
          addToast("file", "📁 File Processed", `${filename} — ${chunks} chunks indexed`, 4000, "interviews");
          break;
        }
        case "suggestion": {
          const msg = event.data.message as string;
          // Suggestions get action buttons
          const toast: Toast = {
            id: `toast-${nextId++}`,
            type: "suggestion",
            title: "💡 Suggestion",
            message: msg,
            timestamp: Date.now(),
            duration: 0, // Sticky
            navigateTo: "chat",
            actions: [
              { label: "Yes, go ahead", onClick: () => {} },
              { label: "Not now", onClick: () => {} },
            ],
          };
          setToasts((prev) => [...prev.slice(-4), toast]);
          break;
        }
        case "finding_created": {
          addToast("info", "🔍 New Finding", event.data.message as string || "New research finding added.", 4000, "findings");
          break;
        }
        case "resource_throttle": {
          const reason = event.data.reason as string;
          addToast("warning", "⏸ Agent Paused", `Hardware throttle: ${reason}`, 10000, "agents");
          break;
        }
        case "task_queue_update": {
          const pending = event.data.pending as number;
          const inProgress = event.data.in_progress as number;
          const completed = event.data.completed as number;
          if (pending > 0 || inProgress > 0) {
            addToast("info", "📊 Queue Update", `${pending} pending, ${inProgress} active, ${completed} done`, 4000, "tasks");
          }
          break;
        }
      }
    },
    [addToast]
  );

  useWebSocket(handleEvent);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-16 right-4 z-50 space-y-2 max-w-sm">
      {toasts.map((toast) => {
        const Icon = ICONS[toast.type];
        return (
          <div
            key={toast.id}
            onClick={() => {
              if (toast.navigateTo) {
                window.dispatchEvent(new CustomEvent("reclaw:navigate", { detail: { view: toast.navigateTo } }));
              }
              removeToast(toast.id);
            }}
            className={cn(
              "animate-fade-in border-l-4 rounded-lg shadow-lg p-3 cursor-pointer",
              COLORS[toast.type]
            )}
          >
            <div className="flex items-start gap-3">
              <Icon size={18} className={cn("shrink-0 mt-0.5", ICON_COLORS[toast.type])} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 dark:text-white">
                  {toast.title}
                </p>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                  {toast.message}
                </p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); removeToast(toast.id); }}
                className="p-0.5 rounded hover:bg-black/5 dark:hover:bg-white/5"
                aria-label="Dismiss notification"
              >
                <X size={14} className="text-slate-400" />
              </button>
            </div>
            {toast.actions && toast.actions.length > 0 && (
              <div className="flex gap-2 mt-2 pl-8">
                {toast.actions.map((action, i) => (
                  <button
                    key={i}
                    onClick={(e) => { e.stopPropagation(); action.onClick(); removeToast(toast.id); }}
                    className={cn(
                      "text-xs px-2 py-1 rounded",
                      i === 0
                        ? "bg-reclaw-600 text-white hover:bg-reclaw-700"
                        : "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-300"
                    )}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
