"use client";

import { useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";

interface AutoSaveWarningProps {
  hasUnsavedChanges: boolean;
}

/**
 * Warns user before navigating away with unsaved changes.
 * Also shows a small inline indicator.
 */
export default function AutoSaveWarning({ hasUnsavedChanges }: AutoSaveWarningProps) {
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [hasUnsavedChanges]);

  if (!hasUnsavedChanges) return null;

  return (
    <div className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400">
      <AlertCircle size={12} />
      <span>Unsaved changes</span>
    </div>
  );
}
