"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  CheckCircle,
  AlertTriangle,
  Info,
  X,
  FileText,
  Lightbulb,
  Cpu,
  Bell,
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

interface NotificationHistoryItem {
  id: string;
  type: Toast["type"];
  title: string;
  message: string;
  timestamp: number;
  navigateTo?: string;
  read: boolean;
}

const MAX_HISTORY = 50;

const ICONS = {
  success: CheckCircle,
  warning: AlertTriangle,
  info: Info,
  agent: Cpu,
  file: FileText,
  suggestion: Lightbulb,
};

const COLORS = {
  success: "border-green-500 bg-green-50 dark:bg-green-900/80",
  warning: "border-yellow-500 bg-yellow-50 dark:bg-yellow-900/80",
  info: "border-blue-500 bg-blue-50 dark:bg-blue-900/80",
  agent: "border-istara-500 bg-istara-50 dark:bg-istara-900/80",
  file: "border-purple-500 bg-purple-50 dark:bg-purple-900/80",
  suggestion: "border-amber-500 bg-amber-50 dark:bg-amber-900/80",
};

const ICON_COLORS = {
  success: "text-green-600",
  warning: "text-yellow-600",
  info: "text-blue-600",
  agent: "text-istara-600",
  file: "text-purple-600",
  suggestion: "text-amber-600",
};

let nextId = 0;

export default function ToastNotification() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [history, setHistory] = useState<NotificationHistoryItem[]>([]);
  const bellRef = useRef<HTMLButtonElement>(null);

  const unreadCount = history.filter((n) => !n.read).length;

  const addToHistory = useCallback((toast: Toast) => {
    const item: NotificationHistoryItem = {
      id: toast.id,
      type: toast.type,
      title: toast.title,
      message: toast.message,
      timestamp: toast.timestamp,
      navigateTo: toast.navigateTo,
      read: false,
    };
    setHistory((prev) => [item, ...prev].slice(0, MAX_HISTORY));
  }, []);

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
      addToHistory(toast);
    },
    [addToHistory]
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
          addToHistory(toast);
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
        case "document_created": {
          const docTitle = (event.data.title as string) || "New document";
          addToast("file", "📄 Document Created", docTitle, 4000, "documents");
          break;
        }
        case "document_updated": {
          const updatedTitle = (event.data.title as string) || "Document updated";
          addToast("file", "📝 Document Updated", updatedTitle, 3000, "documents");
          break;
        }
      }
    },
    [addToast, addToHistory]
  );

  useWebSocket(handleEvent);

  // Global toast API — any component can dispatch istara:toast to show a toast
  useEffect(() => {
    const handler = (e: Event) => {
      const { type, title, message, duration, navigateTo } = (e as CustomEvent).detail || {};
      if (title && message) {
        addToast(type || "info", title, message, duration, navigateTo);
      }
    };
    window.addEventListener("istara:toast", handler);
    return () => window.removeEventListener("istara:toast", handler);
  }, [addToast]);

  return (
    <>
      {/* Bell icon button — navigates to Notifications view */}
      <div className="fixed bottom-16 right-[calc(1rem+24rem+0.5rem)] z-50 sm:right-[calc(1rem+24rem+0.5rem)]">
        <button
          ref={bellRef}
          onClick={() => {
            window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "notifications" }));
          }}
          aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ""}`}
          className={cn(
            "relative p-2 rounded-full shadow-lg transition-colors",
            "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700",
            "hover:bg-slate-100 dark:hover:bg-slate-700",
            "focus:outline-none focus:ring-2 focus:ring-istara-500 focus:ring-offset-2 dark:focus:ring-offset-slate-900"
          )}
        >
          <Bell size={20} className="text-slate-600 dark:text-slate-300" />
          {unreadCount > 0 && (
            <span
              className="absolute -top-1 -right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-600 rounded-full"
              aria-hidden="true"
            >
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </button>
      </div>

      {/* Toast notifications */}
      {toasts.length > 0 && (
        <div
          className="fixed bottom-16 right-4 z-50 space-y-2 max-w-sm"
          role="status"
          aria-live="polite"
          aria-label="Toast notifications"
        >
          {toasts.map((toast) => {
            const Icon = ICONS[toast.type];
            return (
              <div
                key={toast.id}
                onClick={() => {
                  if (toast.navigateTo) {
                    window.dispatchEvent(new CustomEvent("istara:navigate", { detail: { view: toast.navigateTo } }));
                  }
                  removeToast(toast.id);
                }}
                className={cn(
                  "animate-fade-in border-l-4 rounded-lg shadow-lg p-3 cursor-pointer",
                  COLORS[toast.type]
                )}
                role="alert"
              >
                <div className="flex items-start gap-3">
                  <Icon size={18} className={cn("shrink-0 mt-0.5", ICON_COLORS[toast.type])} aria-hidden="true" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">
                      {toast.title}
                    </p>
                    <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5">
                      {toast.message}
                    </p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); removeToast(toast.id); }}
                    className={cn(
                      "p-0.5 rounded hover:bg-black/10 dark:hover:bg-white/10",
                      "focus:outline-none focus:ring-2 focus:ring-istara-500"
                    )}
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
                          "focus:outline-none focus:ring-2 focus:ring-istara-500",
                          i === 0
                            ? "bg-istara-600 text-white hover:bg-istara-700"
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
          {/* View All link */}
          <button
            onClick={() => {
              window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "notifications" }));
            }}
            className="w-full text-center text-xs text-istara-600 dark:text-istara-400 hover:text-istara-700 dark:hover:text-istara-300 py-1.5 bg-white/80 dark:bg-slate-800/80 rounded-lg border border-slate-200 dark:border-slate-700 backdrop-blur"
          >
            View All
          </button>
        </div>
      )}
    </>
  );
}
