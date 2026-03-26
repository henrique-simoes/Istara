"use client";

import { useEffect } from "react";
import { Activity, Clock, RefreshCw, Plus, History } from "lucide-react";
import { useLoopsStore } from "@/stores/loopsStore";
import { cn } from "@/lib/utils";
import LoopOverviewTab from "./LoopOverviewTab";
import SchedulesTab from "./SchedulesTab";
import AgentLoopsTab from "./AgentLoopsTab";
import CustomLoopsTab from "./CustomLoopsTab";
import ExecutionHistoryTab from "./ExecutionHistoryTab";

type LoopsTab = "overview" | "schedules" | "agent-loops" | "custom" | "history";

const TABS: { id: LoopsTab; icon: any; label: string }[] = [
  { id: "overview", icon: Activity, label: "Overview" },
  { id: "schedules", icon: Clock, label: "Schedules" },
  { id: "agent-loops", icon: RefreshCw, label: "Agent Loops" },
  { id: "custom", icon: Plus, label: "Custom" },
  { id: "history", icon: History, label: "History" },
];

export default function LoopsView() {
  const { activeTab, setActiveTab, fetchOverview, fetchHealth } = useLoopsStore();

  useEffect(() => {
    fetchOverview();
    fetchHealth();
  }, [fetchOverview, fetchHealth]);

  const renderTab = () => {
    switch (activeTab) {
      case "overview": return <LoopOverviewTab />;
      case "schedules": return <SchedulesTab />;
      case "agent-loops": return <AgentLoopsTab />;
      case "custom": return <CustomLoopsTab />;
      case "history": return <ExecutionHistoryTab />;
      default: return <LoopOverviewTab />;
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors",
              activeTab === tab.id
                ? "bg-reclaw-100 text-reclaw-700 dark:bg-reclaw-900/30 dark:text-reclaw-400"
                : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            )}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Active tab content */}
      {renderTab()}
    </div>
  );
}
