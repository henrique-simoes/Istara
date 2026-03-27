"use client";

import { useEffect } from "react";
import { MessageSquare, BarChart3, FileQuestion, Plug, Rocket } from "lucide-react";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { cn } from "@/lib/utils";
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
  const { activeTab, setActiveTab, fetchChannels } = useIntegrationsStore();

  useEffect(() => {
    fetchChannels();
  }, [fetchChannels]);

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
