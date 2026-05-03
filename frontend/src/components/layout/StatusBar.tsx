"use client";

import { useEffect, useState } from "react";
import { Wifi, WifiOff, Cpu, HardDrive } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { WSEvent } from "@/lib/types";

import { API_BASE } from "@/lib/runtimeConfig";

function IstaraVersion() {
  const [version, setVersion] = useState("...");
  useEffect(() => {
    fetch(`${API_BASE}/api/updates/version`)
      .then(r => r.json())
      .then(d => setVersion(d.version || "dev"))
      .catch(() => setVersion("dev"));
  }, []);
  return <span>🐾 Istara v{version}</span>;
}

export default function StatusBar() {
  const [agentStatus, setAgentStatus] = useState("Idle");
  const [agentDetail, setAgentDetail] = useState("");
  const [llmStatus, setLlmStatus] = useState<"ok" | "slow" | "down">("ok");
  const [serverOnline, setServerOnline] = useState<boolean | null>(null);

  const handleEvent = (event: WSEvent) => {
    switch (event.type) {
      case "agent_status":
        setAgentStatus(event.data.status as string || "Working");
        setAgentDetail(event.data.details as string || "");
        break;
      case "task_progress":
        setAgentStatus("Working");
        setAgentDetail(`Task progress: ${Math.round((event.data.progress as number || 0) * 100)}%`);
        break;
      case "file_processed":
        setAgentStatus("Processed file");
        setAgentDetail(event.data.filename as string || "");
        setTimeout(() => { setAgentStatus("Idle"); setAgentDetail(""); }, 3000);
        break;
      case "llm_unavailable":
        setLlmStatus("down");
        break;
      case "llm_degraded":
        setLlmStatus("slow");
        break;
      case "llm_recovered":
        setLlmStatus("ok");
        window.dispatchEvent(new CustomEvent("istara:toast", {
          detail: { type: "success", title: "LLM Recovered", message: "LLM server is back online." },
        }));
        break;
      case "agent_thinking":
        setAgentStatus("Thinking");
        setAgentDetail(`Step ${event.data.step}/${event.data.total_steps}: ${((event.data.thought as string) || "").substring(0, 80)}`);
        break;
      case "plan_progress":
        setAgentStatus("Executing Plan");
        setAgentDetail(`Step ${event.data.plan_step}/${event.data.total_steps}: ${event.data.step_description} [${event.data.step_status}]`);
        break;
    }
  };

  const { connected, status: realtimeStatus, lastCloseReason } = useWebSocket(handleEvent);

  useEffect(() => {
    let cancelled = false;
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
        if (!cancelled) setServerOnline(res.ok);
      } catch {
        if (!cancelled) setServerOnline(false);
      }
    };
    checkHealth();
    const timer = window.setInterval(checkHealth, 10000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const connectionLabel = !serverOnline
    ? "Server offline"
    : connected
      ? "Live updates connected"
      : realtimeStatus === "auth_failed"
        ? "Live updates need login"
        : realtimeStatus === "connecting"
          ? "Live updates connecting"
          : "Live updates reconnecting";
  const connectionTitle = connected
    ? "Live agent, task, document, and notification updates are connected."
    : serverOnline
      ? `The backend HTTP API is online, but the live-events WebSocket is not connected${lastCloseReason ? `: ${lastCloseReason}` : "."}`
      : "Istara cannot reach the backend health endpoint.";

  return (
    <footer className="flex items-center justify-between px-4 py-1.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-xs text-slate-500 dark:text-slate-400">
      <div className="flex items-center gap-4">
        {/* Connection status */}
        <div className="flex items-center gap-1.5" title={connectionTitle}>
          {serverOnline && connected ? (
            <>
              <Wifi size={12} className="text-green-500" />
              <span>{connectionLabel}</span>
            </>
          ) : (
            <>
              <WifiOff size={12} className={serverOnline ? "text-amber-500" : "text-red-500"} />
              <span>{connectionLabel}</span>
            </>
          )}
        </div>

        {/* Agent status */}
        <div className="flex items-center gap-1.5">
          <Cpu size={12} />
          <span>
            {agentStatus}
            {agentDetail && ` — ${agentDetail}`}
          </span>
        </div>

        {/* LLM health banner */}
        {llmStatus === "down" && (
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded font-medium">
            <WifiOff size={12} />
            LLM unavailable — agent work paused
          </div>
        )}
        {llmStatus === "slow" && (
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded">
            <Wifi size={12} />
            LLM responding slowly
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        <span className="hidden sm:inline">Press <kbd className="px-1 py-0.5 bg-slate-200 dark:bg-slate-700 rounded text-[10px]">?</kbd> for shortcuts</span>
        <IstaraVersion />
      </div>
    </footer>
  );
}
