"use client";

import { useEffect } from "react";
import { X } from "lucide-react";
import FocusTrap from "./FocusTrap";

interface KeyboardShortcutsProps {
  open: boolean;
  onClose: () => void;
}

const SHORTCUTS = [
  { keys: ["⌘", "K"], action: "Search findings" },
  { keys: ["⌘", "1"], action: "Chat view" },
  { keys: ["⌘", "2"], action: "Findings view" },
  { keys: ["⌘", "3"], action: "Tasks view" },
  { keys: ["⌘", "4"], action: "Interviews view" },
  { keys: ["⌘", "5"], action: "Context view" },
  { keys: ["⌘", "6"], action: "Skills view" },
  { keys: ["⌘", "7"], action: "Agents view" },
  { keys: ["⌘", "N"], action: "New project" },
  { keys: ["⌘", "."], action: "Toggle right panel" },
  { keys: ["Esc"], action: "Close modal / cancel" },
  { keys: ["?"], action: "Show this help" },
];

export default function KeyboardShortcuts({ open, onClose }: KeyboardShortcutsProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <FocusTrap>
        <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl max-w-sm w-full p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-900 dark:text-white">⌨️ Keyboard Shortcuts</h3>
            <button onClick={onClose} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800">
              <X size={16} className="text-slate-400" />
            </button>
          </div>
          <div className="space-y-2">
            {SHORTCUTS.map((s) => (
              <div key={s.action} className="flex items-center justify-between py-1">
                <span className="text-sm text-slate-600 dark:text-slate-400">{s.action}</span>
                <div className="flex gap-1">
                  {s.keys.map((k) => (
                    <kbd key={k} className="px-1.5 py-0.5 text-xs bg-slate-100 dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-700 font-mono">
                      {k}
                    </kbd>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </FocusTrap>
    </div>
  );
}
