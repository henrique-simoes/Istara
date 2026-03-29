"use client";

import { useEffect } from "react";
import { LayoutDashboard, FlaskConical, Trophy, Settings } from "lucide-react";
import { useAutoresearchStore } from "@/stores/autoresearchStore";
import { cn } from "@/lib/utils";
import ExperimentDashboard from "./ExperimentDashboard";
import ExperimentHistory from "./ExperimentHistory";
import LeaderboardTab from "./LeaderboardTab";
import ConfigPanel from "./ConfigPanel";
import ViewOnboarding from "@/components/common/ViewOnboarding";

type AutoresearchTab = "dashboard" | "experiments" | "leaderboard" | "config";

const TABS: { id: AutoresearchTab; icon: any; label: string }[] = [
  { id: "dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { id: "experiments", icon: FlaskConical, label: "Experiments" },
  { id: "leaderboard", icon: Trophy, label: "Leaderboard" },
  { id: "config", icon: Settings, label: "Config" },
];

export default function AutoresearchView() {
  const { activeTab, setActiveTab, fetchStatus } = useAutoresearchStore();

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const renderTab = () => {
    switch (activeTab) {
      case "dashboard":
        return <ExperimentDashboard />;
      case "experiments":
        return <ExperimentHistory />;
      case "leaderboard":
        return <LeaderboardTab />;
      case "config":
        return <ConfigPanel />;
      default:
        return <ExperimentDashboard />;
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <ViewOnboarding viewId="autoresearch" title="Autonomous Research" description="Self-improving research loops — agents experiment with strategies and models. Leaderboard shows what works best." chatPrompt="How does autoresearch work?" />
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            aria-label={tab.label}
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
