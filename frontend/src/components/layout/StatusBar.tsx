"use client";

import { useEffect, useState } from "react";
import { Wifi, WifiOff, Cpu, HardDrive } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { WSEvent } from "@/lib/types";

export default function StatusBar() {
  const [agentStatus, setAgentStatus] = useState("Idle");
  const [agentDetail, setAgentDetail] = useState("");

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
        setTimeout(() => {
          setAgentStatus("Idle");
          setAgentDetail("");
        }, 3000);
        break;
    }
  };

  const { connected } = useWebSocket(handleEvent);

  return (
    <footer className="flex items-center justify-between px-4 py-1.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-xs text-slate-500 dark:text-slate-400">
      <div className="flex items-center gap-4">
        {/* Connection status */}
        <div className="flex items-center gap-1.5">
          {connected ? (
            <>
              <Wifi size={12} className="text-green-500" />
              <span>Connected</span>
            </>
          ) : (
            <>
              <WifiOff size={12} className="text-red-500" />
              <span>Disconnected</span>
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
      </div>

      <div className="flex items-center gap-4">
        <span className="hidden sm:inline">Press <kbd className="px-1 py-0.5 bg-slate-200 dark:bg-slate-700 rounded text-[10px]">?</kbd> for shortcuts</span>
        <span>🐾 Istara v{process.env.npm_package_version || "0.1.0"}</span>
      </div>
    </footer>
  );
}
