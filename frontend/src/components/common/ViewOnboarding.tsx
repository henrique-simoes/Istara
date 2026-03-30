"use client";

import { useEffect, useRef } from "react";
import { X, MessageSquare, Lightbulb } from "lucide-react";
import { useViewOnboarding } from "@/hooks/useViewOnboarding";
import { cn } from "@/lib/utils";

interface ViewOnboardingAction {
  label: string;
  onClick: () => void;
}

interface ViewOnboardingProps {
  /** Unique key for localStorage persistence (e.g. "chat", "findings") */
  viewId: string;
  /** Short title (e.g. "Your Research Assistant") */
  title: string;
  /** 1-2 sentence feature explanation */
  description: string;
  /** Quick action buttons (max 3) */
  actions?: ViewOnboardingAction[];
  /** Suggested prompt for Chat (e.g. "What can I do in Findings?") */
  chatPrompt?: string;
}

/**
 * Non-blocking inline onboarding banner for any view.
 *
 * Shows once per view (dismissal persisted to localStorage).
 * Informative but direct — doesn't block the UI.
 * Mentions Chat can answer questions about the feature.
 */
export default function ViewOnboarding({
  viewId,
  title,
  description,
  actions,
  chatPrompt,
}: ViewOnboardingProps) {
  const { visible, dismiss } = useViewOnboarding(viewId);
  const closeRef = useRef<HTMLButtonElement>(null);

  // Escape key to dismiss
  useEffect(() => {
    if (!visible) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") dismiss();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [visible, dismiss]);

  if (!visible) return null;

  return (
    <div
      role="region"
      aria-label={`${title} onboarding`}
      aria-live="polite"
      className="mx-4 mt-3 mb-1 rounded-lg border border-istara-200 dark:border-istara-800 bg-istara-50 dark:bg-istara-900/20 p-4 relative"
    >
      {/* Dismiss button */}
      <button
        ref={closeRef}
        onClick={dismiss}
        className="absolute top-3 right-3 p-1 rounded-md text-istara-400 hover:text-istara-600 dark:hover:text-istara-300 hover:bg-istara-100 dark:hover:bg-istara-800/40 transition-colors"
        aria-label="Dismiss hint"
      >
        <X size={16} />
      </button>

      {/* Content */}
      <div className="flex items-start gap-3 pr-8">
        <Lightbulb size={20} className="text-istara-500 shrink-0 mt-0.5" aria-hidden="true" />
        <div className="space-y-2 min-w-0">
          <div>
            <h3 className="text-sm font-semibold text-istara-800 dark:text-istara-300">
              {title}
            </h3>
            <p className="text-xs text-istara-600 dark:text-istara-400 mt-0.5 leading-relaxed">
              {description}
            </p>
          </div>

          {/* Action buttons */}
          {actions && actions.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {actions.map((action, i) => (
                <button
                  key={i}
                  onClick={action.onClick}
                  className={cn(
                    "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                    i === 0
                      ? "bg-istara-600 text-white hover:bg-istara-700"
                      : "bg-istara-100 dark:bg-istara-800/40 text-istara-700 dark:text-istara-300 hover:bg-istara-200 dark:hover:bg-istara-800/60"
                  )}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}

          {/* Chat hint */}
          <p className="text-[11px] text-istara-500 dark:text-istara-500 flex items-center gap-1">
            <MessageSquare size={10} aria-hidden="true" />
            {chatPrompt
              ? <>Try asking: &ldquo;{chatPrompt}&rdquo;</>
              : <>Chat knows about this feature — ask questions there.</>
            }
          </p>
        </div>
      </div>
    </div>
  );
}
