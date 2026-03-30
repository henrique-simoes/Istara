"use client";

import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { X } from "lucide-react";

interface TourAction {
  label: string;
  onClick: () => void;
  variant?: "primary" | "secondary" | "ghost";
}

interface TourPopoverProps {
  /** CSS selector for the target element to anchor to (e.g., "#tour-target-team-mode"). Null = centered. */
  targetSelector: string | null;
  /** Preferred placement relative to target. */
  placement?: "top" | "bottom" | "left" | "right";
  title: string;
  description: string | ReactNode;
  actions: TourAction[];
  stepNumber: number;
  totalSteps: number;
  onSkip: () => void;
  /** Show spotlight overlay around target. */
  spotlight?: boolean;
}

export default function TourPopover({
  targetSelector,
  placement = "bottom",
  title,
  description,
  actions,
  stepNumber,
  totalSteps,
  onSkip,
  spotlight = true,
}: TourPopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number; targetRect: DOMRect | null }>({
    top: 0,
    left: 0,
    targetRect: null,
  });
  const [visible, setVisible] = useState(false);

  // Position the popover relative to the target element
  useLayoutEffect(() => {
    const update = () => {
      if (!targetSelector) {
        // Centered on screen
        setPos({ top: window.innerHeight / 2 - 120, left: window.innerWidth / 2 - 200, targetRect: null });
        setVisible(true);
        return;
      }

      const el = document.querySelector(targetSelector);
      if (!el) return;

      const rect = el.getBoundingClientRect();
      const popW = 400;
      const popH = 240;
      const gap = 16;

      let top = 0;
      let left = 0;

      switch (placement) {
        case "top":
          top = rect.top - popH - gap;
          left = rect.left + rect.width / 2 - popW / 2;
          break;
        case "bottom":
          top = rect.bottom + gap;
          left = rect.left + rect.width / 2 - popW / 2;
          break;
        case "left":
          top = rect.top + rect.height / 2 - popH / 2;
          left = rect.left - popW - gap;
          break;
        case "right":
          top = rect.top + rect.height / 2 - popH / 2;
          left = rect.right + gap;
          break;
      }

      // Keep within viewport
      left = Math.max(16, Math.min(left, window.innerWidth - popW - 16));
      top = Math.max(16, Math.min(top, window.innerHeight - popH - 16));

      setPos({ top, left, targetRect: rect });
      setVisible(true);
    };

    // Wait for DOM to settle
    const timer = setTimeout(update, 100);
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);

    // Also observe DOM changes in case target renders asynchronously
    const observer = new MutationObserver(() => setTimeout(update, 50));
    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      clearTimeout(timer);
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
      observer.disconnect();
    };
  }, [targetSelector, placement]);

  // Auto-scroll target into view
  useEffect(() => {
    if (!targetSelector) return;
    const el = document.querySelector(targetSelector);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [targetSelector]);

  // Focus popover on mount for accessibility
  useEffect(() => {
    if (visible && popoverRef.current) {
      popoverRef.current.focus();
    }
  }, [visible]);

  if (!visible) return null;

  const progress = ((stepNumber + 1) / totalSteps) * 100;

  return (
    <>
      {/* Spotlight overlay — dims everything except the target */}
      {spotlight && pos.targetRect && (
        <div
          className="fixed inset-0 z-[998] pointer-events-none"
          aria-hidden="true"
        >
          {/* Semi-transparent overlay with cutout */}
          <div
            className="absolute"
            style={{
              top: pos.targetRect.top - 8,
              left: pos.targetRect.left - 8,
              width: pos.targetRect.width + 16,
              height: pos.targetRect.height + 16,
              borderRadius: "12px",
              boxShadow: "0 0 0 9999px rgba(0, 0, 0, 0.45)",
            }}
          />
        </div>
      )}

      {/* Popover card */}
      <div
        ref={popoverRef}
        role="dialog"
        aria-label={title}
        aria-modal="false"
        tabIndex={-1}
        className="fixed z-[999] w-[400px] max-w-[calc(100vw-32px)] bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-300"
        style={{ top: pos.top, left: pos.left }}
      >
        {/* Progress bar */}
        <div className="h-1 bg-slate-100 dark:bg-slate-800">
          <div
            className="h-full bg-istara-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="p-5">
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="text-xs text-slate-400 dark:text-slate-500 mb-1">
                Step {stepNumber + 1} of {totalSteps}
              </p>
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                {title}
              </h3>
            </div>
            <button
              onClick={onSkip}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              aria-label="Skip tour"
            >
              <X size={16} />
            </button>
          </div>

          {/* Description */}
          <div className="text-sm text-slate-600 dark:text-slate-400 mb-5 leading-relaxed">
            {description}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between">
            <button
              onClick={onSkip}
              className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition"
            >
              Skip tour
            </button>
            <div className="flex gap-2">
              {actions.map((action, i) => (
                <button
                  key={i}
                  onClick={action.onClick}
                  className={
                    action.variant === "secondary"
                      ? "px-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                      : action.variant === "ghost"
                      ? "px-4 py-2 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition"
                      : "px-4 py-2 text-sm rounded-lg bg-istara-600 hover:bg-istara-700 text-white font-medium transition"
                  }
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
