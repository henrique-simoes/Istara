"use client";

import { useState, useCallback, useEffect } from "react";

const PREFIX = "istara_onboarding_";

/**
 * Hook for per-view onboarding dismissal state.
 * Persists to localStorage so hints show only once per view.
 */
export function useViewOnboarding(viewId: string) {
  const key = `${PREFIX}${viewId}`;

  const [visible, setVisible] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      return localStorage.getItem(key) !== "dismissed";
    } catch {
      return true;
    }
  });

  const dismiss = useCallback(() => {
    setVisible(false);
    try {
      localStorage.setItem(key, "dismissed");
    } catch {}
  }, [key]);

  const reset = useCallback(() => {
    setVisible(true);
    try {
      localStorage.removeItem(key);
    } catch {}
  }, [key]);

  return { visible, dismiss, reset };
}

/**
 * Reset ALL onboarding hints across all views.
 * Called from Settings > "Reset Onboarding Hints".
 */
export function resetAllOnboarding() {
  if (typeof window === "undefined") return;
  try {
    const keys = Object.keys(localStorage).filter((k) => k.startsWith(PREFIX));
    keys.forEach((k) => localStorage.removeItem(k));
  } catch {}
}
