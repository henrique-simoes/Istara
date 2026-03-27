"use client";

import { useEffect, useState } from "react";
import { MessageSquare, Rocket, FileQuestion, Plug, ArrowRight, Activity } from "lucide-react";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { cn } from "@/lib/utils";

interface StatCard {
  label: string;
  value: number;
  icon: any;
  color: string;
  tab: "messaging" | "deployments" | "surveys" | "mcp";
}

export default function IntegrationsOverview() {
  const {
    channelInstances,
    deploymentsList,
    surveyIntegrations,
    mcpClients,
    channelLoading,
    fetchChannels,
    fetchDeployments,
    fetchSurveyIntegrations,
    fetchMCPClients,
    setActiveTab,
  } = useIntegrationsStore();

  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    Promise.all([
      fetchChannels(),
      fetchDeployments(),
      fetchSurveyIntegrations(),
      fetchMCPClients(),
    ]).finally(() => setLoaded(true));
  }, [fetchChannels, fetchDeployments, fetchSurveyIntegrations, fetchMCPClients]);

  const activeChannels = channelInstances.filter((c) => c.is_active).length;
  const activeDeployments = deploymentsList.filter((d) => d.state === "active").length;
  const totalSurveyResponses = surveyIntegrations.length;
  const totalMCPTools = mcpClients.reduce((acc, c) => acc + (c.tools?.length || 0), 0);

  const stats: StatCard[] = [
    { label: "Channels Active", value: activeChannels, icon: MessageSquare, color: "text-blue-500", tab: "messaging" },
    { label: "Deployments Running", value: activeDeployments, icon: Rocket, color: "text-purple-500", tab: "deployments" },
    { label: "Survey Integrations", value: totalSurveyResponses, icon: FileQuestion, color: "text-green-500", tab: "surveys" },
    { label: "MCP Tools Available", value: totalMCPTools, icon: Plug, color: "text-amber-500", tab: "mcp" },
  ];

  // Build recent activity from channel instances + deployments
  const recentActivity = [
    ...channelInstances.slice(0, 3).map((c) => ({
      id: c.id,
      type: "channel" as const,
      label: `${c.platform} channel "${c.name}"`,
      detail: c.is_active ? "Active" : "Inactive",
      time: c.updated_at,
    })),
    ...deploymentsList.slice(0, 3).map((d) => ({
      id: d.id,
      type: "deployment" as const,
      label: `${d.deployment_type} "${d.name}"`,
      detail: `${d.current_responses}/${d.target_responses} responses`,
      time: d.updated_at,
    })),
  ].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime()).slice(0, 6);

  if (!loaded) {
    return (
      <div className="flex-1 p-6 space-y-6 overflow-y-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse" />
          ))}
        </div>
        <div className="h-64 rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 dark:text-white">Integrations</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Manage messaging channels, research deployments, survey platforms, and MCP connections.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <button
            key={stat.label}
            onClick={() => setActiveTab(stat.tab)}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 text-left hover:border-reclaw-300 dark:hover:border-reclaw-700 transition-colors group"
          >
            <div className="flex items-center justify-between mb-3">
              <stat.icon size={20} className={stat.color} />
              <ArrowRight size={14} className="text-slate-300 dark:text-slate-600 group-hover:text-reclaw-500 transition-colors" />
            </div>
            <div className="text-2xl font-bold text-slate-900 dark:text-white">{stat.value}</div>
            <div className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{stat.label}</div>
          </button>
        ))}
      </div>

      {/* Recent Activity */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-200 dark:border-slate-800">
          <Activity size={16} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Recent Activity</h2>
        </div>

        {recentActivity.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <MessageSquare size={32} className="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">No integrations configured yet</p>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              Connect messaging channels, deploy research, or add survey platforms to get started.
            </p>
            <button
              onClick={() => setActiveTab("messaging")}
              className="mt-4 px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 transition-colors"
            >
              Add First Channel
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {recentActivity.map((item) => (
              <div key={item.id} className="flex items-center justify-between px-5 py-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className={cn(
                    "w-2 h-2 rounded-full shrink-0",
                    item.type === "channel" ? "bg-blue-500" : "bg-purple-500"
                  )} />
                  <div className="min-w-0">
                    <p className="text-sm text-slate-900 dark:text-white truncate">{item.label}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{item.detail}</p>
                  </div>
                </div>
                <span className="text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap ml-4">
                  {new Date(item.time).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
