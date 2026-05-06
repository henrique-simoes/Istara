"use client";

import { useState, useEffect, useCallback } from "react";
import { detectLocalLLM, type LocalLLMDetection } from "@/lib/modelProviders";

/**
 * Detects a local LLM server running on the user's machine.
 *
 * This works from any browser — even when the page is served from a remote server.
 * The browser can fetch from localhost when the model server enables CORS.
 *
 * Use case: "Donate AI compute" toggle on login screen. If the user has an LLM
 * server running locally, they can contribute it to the team's compute pool.
 */

export type LocalLLMInfo = LocalLLMDetection;

export function useLocalLLM() {
  const [localLLM, setLocalLLM] = useState<LocalLLMInfo | null>(null);
  const [detecting, setDetecting] = useState(true);

  const detect = useCallback(async () => {
    setDetecting(true);

    setLocalLLM(await detectLocalLLM());
    setDetecting(false);
  }, []);

  useEffect(() => {
    detect();
    // Re-detect every 30 seconds (user might start/stop LM Studio)
    const interval = setInterval(detect, 30000);
    return () => clearInterval(interval);
  }, [detect]);

  return { localLLM, detecting, redetect: detect };
}
