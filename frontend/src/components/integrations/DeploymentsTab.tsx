"use client";

import { useEffect, useState } from "react";
import { Plus, Rocket, MessageSquare, CheckCircle2, Activity, Users } from "lucide-react";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { cn } from "@/lib/utils";
import DeploymentWizard from "./DeploymentWizard";
import DeploymentDashboard from "./DeploymentDashboard";

const STATE_BADGE: Record<string, { label: string; classes: string }> = {
  draft: { label: "Draft", classes: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400" },
  active: { label: "Active", classes: "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400" },
  paused: { label: "Paused", classes: "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400" },
  completed: { label: "Completed", classes: "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400" },
};

export default function DeploymentsTab() {
  const {
    deploymentsList,
    deploymentLoading,
    selectedDeploymentId,
    fetchDeployments,
    selectDeployment,
  } = useIntegrationsStore();

  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    fetchDeployments();
  }, [fetchDeployments]);

  const selectedDeployment = deploymentsList.find((d) => d.id === selectedDeploymentId);

  // Summary stats
  const totalConversations = deploymentsList.reduce((acc, d) => acc + d.current_responses, 0);
  const completedConversations = deploymentsList.filter((d) => d.state === "completed").reduce((acc, d) => acc + d.current_responses, 0);
  const activeDeployments = deploymentsList.filter((d) => d.state === "active").length;

  if (showWizard) {
    return (
      <DeploymentWizard
        onClose={() => {
          setShowWizard(false);
          fetchDeployments();
        }}
      />
    );
  }

  if (selectedDeployment) {
    return <DeploymentDashboard deployment={selectedDeployment} onBack={() => selectDeployment(null)} />;
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Research Deployments</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Deploy automated research across messaging channels.
          </p>
        </div>
        <button
          onClick={() => setShowWizard(true)}
          className="flex items-center gap-1.5 px-3 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 transition-colors"
        >
          <Plus size={14} />
          New Deployment
        </button>
      </div>

      {/* Summary stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <MessageSquare size={16} className="text-blue-500" />
            <span className="text-xs text-slate-500 dark:text-slate-400">Conversations Started</span>
          </div>
          <span className="text-xl font-bold text-slate-900 dark:text-white">{totalConversations}</span>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 size={16} className="text-green-500" />
            <span className="text-xs text-slate-500 dark:text-slate-400">Completed</span>
          </div>
          <span className="text-xl font-bold text-slate-900 dark:text-white">{completedConversations}</span>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity size={16} className="text-purple-500" />
            <span className="text-xs text-slate-500 dark:text-slate-400">Findings Created</span>
          </div>
          <span className="text-xl font-bold text-slate-900 dark:text-white">--</span>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Rocket size={16} className="text-amber-500" />
            <span className="text-xs text-slate-500 dark:text-slate-400">Active Deployments</span>
          </div>
          <span className="text-xl font-bold text-slate-900 dark:text-white">{activeDeployments}</span>
        </div>
      </div>

      {/* Deployments list */}
      {deploymentLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse" />
          ))}
        </div>
      ) : deploymentsList.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
          <Rocket size={40} className="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">No deployments yet</p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
            Create a deployment to start automated research interviews or surveys through messaging channels.
          </p>
          <button
            onClick={() => setShowWizard(true)}
            className="px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 transition-colors"
          >
            Create First Deployment
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {deploymentsList.map((deployment) => {
            const badge = STATE_BADGE[deployment.state] || STATE_BADGE.draft;
            const progress = deployment.target_responses > 0
              ? Math.round((deployment.current_responses / deployment.target_responses) * 100)
              : 0;

            return (
              <button
                key={deployment.id}
                onClick={() => selectDeployment(deployment.id)}
                className="w-full text-left bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 hover:border-reclaw-300 dark:hover:border-reclaw-700 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{deployment.name}</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 capitalize">
                      {deployment.deployment_type.replace("_", " ")} &middot; {deployment.questions.length} questions
                    </p>
                  </div>
                  <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", badge.classes)}>
                    {badge.label}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
                    <span>{deployment.current_responses} / {deployment.target_responses} responses</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-reclaw-500 rounded-full transition-all"
                      style={{ width: `${Math.min(progress, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-3 mt-3 text-xs text-slate-400 dark:text-slate-500">
                  <span className="flex items-center gap-1">
                    <Users size={12} />
                    {deployment.channel_instance_ids.length} channel{deployment.channel_instance_ids.length !== 1 ? "s" : ""}
                  </span>
                  <span>Created {new Date(deployment.created_at).toLocaleDateString()}</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
