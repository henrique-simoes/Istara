"use client";

import { useEffect, useState } from "react";
import { Wifi, WifiOff, Cpu } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { WSEvent } from "@/lib/types";

import { API_BASE } from "@/lib/runtimeConfig";

type FrontendRuntimeFreshness = {
  stale?: boolean;
  message?: string | null;
  status?: string;
};

function getConnectionLabel(
  serverOnline: boolean | null,
  connected: boolean,
  realtimeStatus: string,
) {
  if (!serverOnline) return "Offline · Server";
  if (connected) return "Connected · Live updates";
  if (realtimeStatus === "auth_failed") return "Login required · Live updates";
  if (realtimeStatus === "connecting") return "Connecting · Live updates";
  return "Reconnecting · Live updates";
}

function splitConnectionLabel(label: string) {
  const separator = label.indexOf(" · ");
  return separator === -1
    ? { state: label, context: "" }
    : { state: label.slice(0, separator), context: label.slice(separator) };
}

type LlmStatus = "ok" | "not_ready" | "slow" | "down";

function applyRealtimeEvent(
  event: WSEvent,
  setAgentStatus: (status: string) => void,
  setAgentDetail: (detail: string) => void,
  setLlmStatus: (status: LlmStatus) => void,
) {
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
}

function useServerHealth() {
  const [serverOnline, setServerOnline] = useState<boolean | null>(null);

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

  return serverOnline;
}

function useLlmHealth() {
  const [llmStatus, setLlmStatus] = useState<LlmStatus>("ok");
  const [runtimeFreshness, setRuntimeFreshness] = useState<FrontendRuntimeFreshness | null>(null);

  useEffect(() => {
    let cancelled = false;
    const checkLLM = async () => {
      try {
        const token = localStorage.getItem("istara_token");
        const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
        const res = await fetch(`${API_BASE}/api/settings/status`, {
          cache: "no-store",
          headers,
        });
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        setRuntimeFreshness(data.runtime?.frontend || null);
        if (!data.llm_readiness?.reachable) {
          setLlmStatus("down");
        } else if (!data.llm_readiness?.chat_ready) {
          setLlmStatus("not_ready");
        } else {
          setLlmStatus("ok");
        }
      } catch {
        if (!cancelled) setLlmStatus("down");
      }
    };
    checkLLM();
    const timer = window.setInterval(checkLLM, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  return { llmStatus, runtimeFreshness };
}

function useStatusBarState() {
  const [agentStatus, setAgentStatus] = useState("Idle");
  const [agentDetail, setAgentDetail] = useState("");
  const [llmEventStatus, setLlmEventStatus] = useState<LlmStatus>("ok");
  const serverOnline = useServerHealth();
  const { llmStatus, runtimeFreshness } = useLlmHealth();
  const handleEvent = (event: WSEvent) => applyRealtimeEvent(event, setAgentStatus, setAgentDetail, setLlmEventStatus);
  const realtime = useWebSocket(handleEvent);

  return {
    agentStatus,
    agentDetail,
    llmStatus: llmEventStatus === "ok" ? llmStatus : llmEventStatus,
    runtimeFreshness,
    serverOnline,
    realtime,
  };
}

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

function ConnectionStatus({
  serverOnline,
  connected,
  realtimeStatus,
  lastCloseReason,
}: {
  serverOnline: boolean | null;
  connected: boolean;
  realtimeStatus: string;
  lastCloseReason?: string | null;
}) {
  const connectionLabel = getConnectionLabel(serverOnline, connected, realtimeStatus);
  const connectionTitle = connected
    ? "Live agent, task, document, and notification updates are connected."
    : serverOnline
      ? `The backend HTTP API is online, but the live-events WebSocket is not connected${lastCloseReason ? `: ${lastCloseReason}` : "."}`
      : "Istara cannot reach the backend health endpoint.";
  const { state: connectionState, context: connectionContext } = splitConnectionLabel(connectionLabel);

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={`System status: ${connectionLabel}`}
      className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-slate-300 dark:border-slate-700 bg-white/70 dark:bg-slate-800/70"
      title={connectionTitle}
    >
      {serverOnline && connected ? (
        <Wifi size={12} className="text-green-500" />
      ) : (
        <WifiOff size={12} className={serverOnline ? "text-amber-500" : "text-red-500"} />
      )}
      <span className="font-medium">System status: <span>{connectionState}</span>{connectionContext}</span>
    </div>
  );
}

function LlmHealthBanner({ status, runtimeFreshness }: { status: LlmStatus; runtimeFreshness: FrontendRuntimeFreshness | null }) {
  return (
    <>
      {status === "down" && (
        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded font-medium">
          <WifiOff size={12} />
          LLM unavailable — agent work paused
        </div>
      )}
      {status === "slow" && (
        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded">
          <Wifi size={12} />
          LLM responding slowly
        </div>
      )}
      {status === "not_ready" && (
        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded">
          <Wifi size={12} />
          LLM connected; chat model not ready
        </div>
      )}
      {runtimeFreshness?.stale && (
        <div
          className="flex items-center gap-1.5 px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded"
          title={runtimeFreshness.message || "The running frontend bundle is older than source changes."}
        >
          <Cpu size={12} />
          Runtime bundle stale
        </div>
      )}
    </>
  );
}

export default function StatusBar() {
  const {
    agentStatus,
    agentDetail,
    llmStatus,
    runtimeFreshness,
    serverOnline,
    realtime: { connected, status: realtimeStatus, lastCloseReason },
  } = useStatusBarState();

  return (
    <footer className="flex items-center justify-between px-4 py-1.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-xs text-slate-500 dark:text-slate-400">
      <div className="flex items-center gap-4">
        <ConnectionStatus
          serverOnline={serverOnline}
          connected={connected}
          realtimeStatus={realtimeStatus}
          lastCloseReason={lastCloseReason}
        />

        {/* Agent status */}
        <div className="flex items-center gap-1.5">
          <Cpu size={12} />
          <span>
            {agentStatus}
            {agentDetail && ` — ${agentDetail}`}
          </span>
        </div>

        <LlmHealthBanner status={llmStatus} runtimeFreshness={runtimeFreshness} />
      </div>

      <div className="flex items-center gap-4">
        <span className="hidden sm:inline">Press <kbd className="px-1 py-0.5 bg-slate-200 dark:bg-slate-700 rounded text-[10px]">?</kbd> for shortcuts</span>
        <IstaraVersion />
      </div>
    </footer>
  );
}
