"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeft, Play, Pause, CheckCircle2, Radio, BarChart3, Users, Search,
  MessageSquare, Clock, TrendingUp,
} from "lucide-react";
import { deployments as deploymentsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ResearchDeployment, DeploymentAnalytics, ChannelConversation } from "@/lib/types";
import ConversationTranscript from "./ConversationTranscript";

type DashboardTab = "live" | "questions" | "participants" | "findings" | "channels" | "timeline";

const TABS: { id: DashboardTab; icon: any; label: string }[] = [
  { id: "live", icon: Radio, label: "Live Feed" },
  { id: "questions", icon: BarChart3, label: "Question Analytics" },
  { id: "participants", icon: Users, label: "Participant Tracker" },
  { id: "findings", icon: Search, label: "Findings Pipeline" },
  { id: "channels", icon: MessageSquare, label: "Channel Performance" },
  { id: "timeline", icon: Clock, label: "Timeline" },
];

interface DeploymentDashboardProps {
  deployment: ResearchDeployment;
  onBack: () => void;
}

export default function DeploymentDashboard({ deployment, onBack }: DeploymentDashboardProps) {
  const [activeTab, setActiveTab] = useState<DashboardTab>("live");
  const [analytics, setAnalytics] = useState<DeploymentAnalytics | null>(null);
  const [conversations, setConversations] = useState<ChannelConversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [transcriptConvId, setTranscriptConvId] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      deploymentsApi.analytics(deployment.id).then(setAnalytics).catch(() => {}),
      deploymentsApi.conversations(deployment.id).then(setConversations).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [deployment.id]);

  const handleActivate = async () => {
    setActionLoading(true);
    try { await deploymentsApi.activate(deployment.id); } catch {} finally { setActionLoading(false); }
  };
  const handlePause = async () => {
    setActionLoading(true);
    try { await deploymentsApi.pause(deployment.id); } catch {} finally { setActionLoading(false); }
  };
  const handleComplete = async () => {
    setActionLoading(true);
    try { await deploymentsApi.complete(deployment.id); } catch {} finally { setActionLoading(false); }
  };

  const progress = deployment.target_responses > 0
    ? Math.round((deployment.current_responses / deployment.target_responses) * 100)
    : 0;

  const renderTabContent = () => {
    if (loading) {
      return (
        <div className="p-6 space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-20 rounded-lg bg-slate-100 dark:bg-slate-800 animate-pulse" />
          ))}
        </div>
      );
    }

    switch (activeTab) {
      case "live": return <LiveFeed conversations={conversations} onViewTranscript={setTranscriptConvId} />;
      case "questions": return <QuestionAnalytics analytics={analytics} />;
      case "participants": return <ParticipantTracker conversations={conversations} onViewTranscript={setTranscriptConvId} />;
      case "findings": return <FindingsPipeline analytics={analytics} />;
      case "channels": return <ChannelPerformance analytics={analytics} deployment={deployment} />;
      case "timeline": return <Timeline deployment={deployment} />;
      default: return null;
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div className="flex items-center gap-3 mb-3">
          <button onClick={onBack} aria-label="Back to deployments" className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <ArrowLeft size={16} />
          </button>
          <div className="flex-1">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">{deployment.name}</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 capitalize">
              {deployment.deployment_type.replace("_", " ")} &middot; {deployment.questions.length} questions
            </p>
          </div>
          <div className="flex items-center gap-2">
            {deployment.state === "draft" && (
              <button onClick={handleActivate} disabled={actionLoading} className="flex items-center gap-1 px-3 py-1.5 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors">
                <Play size={12} /> Activate
              </button>
            )}
            {deployment.state === "active" && (
              <button onClick={handlePause} disabled={actionLoading} className="flex items-center gap-1 px-3 py-1.5 text-xs bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 transition-colors">
                <Pause size={12} /> Pause
              </button>
            )}
            {(deployment.state === "active" || deployment.state === "paused") && (
              <button onClick={handleComplete} disabled={actionLoading} className="flex items-center gap-1 px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
                <CheckCircle2 size={12} /> Complete
              </button>
            )}
          </div>
        </div>

        {/* Progress */}
        <div className="mb-3">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span>{deployment.current_responses} / {deployment.target_responses} responses</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full bg-reclaw-500 rounded-full transition-all" style={{ width: `${Math.min(progress, 100)}%` }} />
          </div>
        </div>

        {/* Sub-tabs */}
        <div className="flex items-center gap-1 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors",
                activeTab === tab.id
                  ? "bg-reclaw-100 text-reclaw-700 dark:bg-reclaw-900/30 dark:text-reclaw-400"
                  : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              )}
            >
              <tab.icon size={12} />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {renderTabContent()}
      </div>

      {/* Transcript overlay */}
      {transcriptConvId && (
        <ConversationTranscript
          deploymentId={deployment.id}
          conversationId={transcriptConvId}
          onClose={() => setTranscriptConvId(null)}
        />
      )}
    </div>
  );
}

// --- Sub-components ---

function LiveFeed({ conversations, onViewTranscript }: { conversations: ChannelConversation[]; onViewTranscript: (id: string) => void }) {
  const active = conversations.filter((c) => c.state === "active");
  const recent = [...conversations].sort((a, b) => {
    const aTime = a.last_message_at || a.started_at;
    const bTime = b.last_message_at || b.started_at;
    return new Date(bTime).getTime() - new Date(aTime).getTime();
  }).slice(0, 10);

  return (
    <div className="p-6 space-y-6">
      {/* Active now */}
      <div>
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
          <Radio size={14} className="text-green-500" />
          Active Now ({active.length})
        </h3>
        {active.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">No active conversations right now.</p>
        ) : (
          <div className="space-y-2">
            {active.map((conv) => (
              <button
                key={conv.id}
                onClick={() => onViewTranscript(conv.id)}
                className="w-full text-left p-3 bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/20 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-900 dark:text-white">{conv.participant_name}</span>
                  <span className="text-xs text-green-600 dark:text-green-400">Q{conv.current_question_index + 1}</span>
                </div>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  Last message: {conv.last_message_at ? new Date(conv.last_message_at).toLocaleTimeString() : "---"}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Recent activity */}
      <div>
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Recent Activity</h3>
        <div className="space-y-2">
          {recent.map((conv) => (
            <button
              key={conv.id}
              onClick={() => onViewTranscript(conv.id)}
              className="w-full text-left p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-900 dark:text-white">{conv.participant_name}</span>
                <span className={cn(
                  "text-xs px-2 py-0.5 rounded-full",
                  conv.state === "completed" ? "bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400" :
                  conv.state === "active" ? "bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400" :
                  "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                )}>
                  {conv.state}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function QuestionAnalytics({ analytics }: { analytics: DeploymentAnalytics | null }) {
  if (!analytics) return <EmptyAnalytics />;

  return (
    <div className="p-6 space-y-4">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Per-Question Statistics</h3>
      {analytics.per_question_stats.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No question data available yet.</p>
      ) : (
        <div className="space-y-3">
          {analytics.per_question_stats.map((qs) => {
            const total = qs.response_count + qs.skip_count;
            const responsePct = total > 0 ? Math.round((qs.response_count / total) * 100) : 0;
            return (
              <div key={qs.index} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <span className="text-xs font-medium text-reclaw-600 dark:text-reclaw-400">Q{qs.index + 1}</span>
                    <p className="text-sm text-slate-900 dark:text-white mt-0.5">{qs.text}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400 mt-2">
                  <span>{qs.response_count} responses</span>
                  <span>{qs.skip_count} skipped</span>
                  <span>{responsePct}% response rate</span>
                </div>
                <div className="h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full mt-2 overflow-hidden">
                  <div className="h-full bg-reclaw-500 rounded-full" style={{ width: `${responsePct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ParticipantTracker({ conversations, onViewTranscript }: { conversations: ChannelConversation[]; onViewTranscript: (id: string) => void }) {
  return (
    <div className="p-6">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">
        Participants ({conversations.length})
      </h3>
      {conversations.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No participants yet.</p>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800">
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">Name</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">State</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">Progress</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">Started</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {conversations.map((conv) => (
              <tr key={conv.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                <td className="px-3 py-2 text-sm text-slate-900 dark:text-white">{conv.participant_name}</td>
                <td className="px-3 py-2">
                  <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full",
                    conv.state === "completed" ? "bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400" :
                    conv.state === "active" ? "bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400" :
                    "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                  )}>
                    {conv.state}
                  </span>
                </td>
                <td className="px-3 py-2 text-sm text-slate-600 dark:text-slate-300">Q{conv.current_question_index + 1}</td>
                <td className="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">{new Date(conv.started_at).toLocaleDateString()}</td>
                <td className="px-3 py-2">
                  <button
                    onClick={() => onViewTranscript(conv.id)}
                    className="text-xs text-reclaw-600 hover:text-reclaw-700 dark:text-reclaw-400 transition-colors"
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function FindingsPipeline({ analytics }: { analytics: DeploymentAnalytics | null }) {
  return (
    <div className="p-6">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Findings Pipeline</h3>
      <div className="text-center py-12 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
        <TrendingUp size={32} className="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Findings will be automatically extracted as conversations complete.
        </p>
        {analytics && (
          <div className="mt-4 flex items-center justify-center gap-6 text-xs text-slate-500 dark:text-slate-400">
            <span>Completed: {analytics.completed_conversations}</span>
            <span>Messages: {analytics.total_messages}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function ChannelPerformance({ analytics, deployment }: { analytics: DeploymentAnalytics | null; deployment: ResearchDeployment }) {
  return (
    <div className="p-6">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Channel Performance</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {deployment.channel_instance_ids.map((chId) => (
          <div key={chId} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4">
            <p className="text-sm font-medium text-slate-900 dark:text-white mb-2 truncate">{chId}</p>
            <div className="text-xs text-slate-500 dark:text-slate-400 space-y-1">
              <p>Response rate: {analytics?.response_rate ? `${Math.round(analytics.response_rate * 100)}%` : "--"}</p>
              <p>Completion rate: {analytics?.completion_rate ? `${Math.round(analytics.completion_rate * 100)}%` : "--"}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Timeline({ deployment }: { deployment: ResearchDeployment }) {
  return (
    <div className="p-6">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">Deployment Timeline</h3>
      <div className="relative pl-6 space-y-6">
        <div className="absolute left-2 top-0 bottom-0 w-px bg-slate-200 dark:bg-slate-700" />

        <TimelineItem time={deployment.created_at} label="Deployment created" />
        {deployment.state !== "draft" && (
          <TimelineItem time={deployment.updated_at} label="Deployment activated" />
        )}
        {deployment.state === "completed" && (
          <TimelineItem time={deployment.updated_at} label="Deployment completed" />
        )}
      </div>
    </div>
  );
}

function TimelineItem({ time, label }: { time: string; label: string }) {
  return (
    <div className="relative flex items-start gap-3">
      <div className="absolute -left-4 w-3 h-3 bg-reclaw-500 rounded-full border-2 border-white dark:border-slate-900" />
      <div>
        <p className="text-sm text-slate-900 dark:text-white">{label}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">{new Date(time).toLocaleString()}</p>
      </div>
    </div>
  );
}

function EmptyAnalytics() {
  return (
    <div className="p-6 text-center py-12">
      <BarChart3 size={32} className="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
      <p className="text-sm text-slate-500 dark:text-slate-400">Analytics data not yet available.</p>
      <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Data will populate as conversations progress.</p>
    </div>
  );
}
