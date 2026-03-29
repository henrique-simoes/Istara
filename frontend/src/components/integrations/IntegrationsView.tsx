"use client";

import { useEffect, useState } from "react";
import { MessageSquare, BarChart3, FileQuestion, Plug, Rocket, Loader2 } from "lucide-react";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { cn } from "@/lib/utils";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import MessagingTab from "./MessagingTab";
import SurveysTab from "./SurveysTab";
import MCPTab from "./MCPTab";
import DeploymentsTab from "./DeploymentsTab";
import IntegrationsOverview from "./IntegrationsOverview";

type IntegrationsTab = "overview" | "messaging" | "surveys" | "mcp" | "deployments";

const TABS: { id: IntegrationsTab; icon: any; label: string }[] = [
  { id: "overview", icon: BarChart3, label: "Overview" },
  { id: "messaging", icon: MessageSquare, label: "Messaging" },
  { id: "surveys", icon: FileQuestion, label: "Surveys" },
  { id: "deployments", icon: Rocket, label: "Deployments" },
  { id: "mcp", icon: Plug, label: "MCP" },
];

export default function IntegrationsView() {
  const { activeTab, setActiveTab, fetchChannels, channelLoading, error } = useIntegrationsStore();
  const [initialLoading, setInitialLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setInitialLoading(true);
    fetchChannels()
      .catch((err: unknown) => {
        console.error("IntegrationsView: failed to fetch channels", err);
      })
      .finally(() => {
        if (!cancelled) setInitialLoading(false);
      });
    return () => { cancelled = true; };
  }, [fetchChannels]);

  // Clear error when switching tabs so one tab's error doesn't block others
  const handleTabChange = (tab: IntegrationsTab) => {
    useIntegrationsStore.setState({ error: null });
    setActiveTab(tab);
  };

  const renderTab = () => {
    switch (activeTab) {
      case "overview": return <IntegrationsOverview />;
      case "messaging": return <MessagingTab />;
      case "surveys": return <SurveysTab />;
      case "deployments": return <DeploymentsTab />;
      case "mcp": return <MCPTab />;
      default: return <IntegrationsOverview />;
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
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
      {initialLoading ? (
        <div className="flex-1 flex items-center justify-center p-8">
          <Loader2 size={24} className="animate-spin text-reclaw-500" />
          <span className="ml-2 text-sm text-slate-400">Loading integrations...</span>
        </div>
      ) : (
        <ErrorBoundary>
          {renderTab()}
        </ErrorBoundary>
      )}
    </div>
  );
}
