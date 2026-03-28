"use client";

import { useState, useEffect, useCallback } from "react";

/**
 * Detects a local LLM server (LM Studio or Ollama) running on the user's machine.
 *
 * This works from any browser — even when the page is served from a remote server.
 * The browser can fetch from localhost because LM Studio/Ollama accept CORS requests.
 *
 * Use case: "Donate AI compute" toggle on login screen. If the user has an LLM
 * server running locally, they can contribute it to the team's compute pool.
 */

export interface LocalLLMInfo {
  provider: "lmstudio" | "ollama";
  host: string;
  models: string[];
  modelCount: number;
}

export function useLocalLLM() {
  const [localLLM, setLocalLLM] = useState<LocalLLMInfo | null>(null);
  const [detecting, setDetecting] = useState(true);

  const detect = useCallback(async () => {
    setDetecting(true);

    // Try LM Studio (port 1234)
    try {
      const res = await fetch("http://localhost:1234/v1/models", {
        signal: AbortSignal.timeout(2000),
      });
      if (res.ok) {
        const data = await res.json();
        const models = (data.data || []).map((m: any) => m.id).filter((id: string) => !id.includes("embed"));
        setLocalLLM({
          provider: "lmstudio",
          host: "http://localhost:1234",
          models,
          modelCount: models.length,
        });
        setDetecting(false);
        return;
      }
    } catch {
      // LM Studio not running — try Ollama
    }

    // Try Ollama (port 11434)
    try {
      const res = await fetch("http://localhost:11434/api/tags", {
        signal: AbortSignal.timeout(2000),
      });
      if (res.ok) {
        const data = await res.json();
        const models = (data.models || []).map((m: any) => m.name);
        setLocalLLM({
          provider: "ollama",
          host: "http://localhost:11434",
          models,
          modelCount: models.length,
        });
        setDetecting(false);
        return;
      }
    } catch {
      // Ollama not running
    }

    setLocalLLM(null);
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
