"use client";

import { useEffect, useState } from "react";
import { RefreshCw, User, Clock, MessageSquare } from "lucide-react";
import { channels as channelsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChannelConversation } from "@/lib/types";

const STATE_BADGE: Record<string, { label: string; classes: string }> = {
  active: { label: "Active", classes: "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400" },
  completed: { label: "Completed", classes: "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400" },
  paused: { label: "Paused", classes: "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400" },
  expired: { label: "Expired", classes: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400" },
};

interface ChannelConversationsPanelProps {
  channelId: string;
}

export default function ChannelConversationsPanel({ channelId }: ChannelConversationsPanelProps) {
  const [conversations, setConversations] = useState<ChannelConversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [stateFilter, setStateFilter] = useState<string | null>(null);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const data = await channelsApi.conversations(channelId);
      setConversations(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [channelId]);

  const filtered = stateFilter
    ? conversations.filter((c) => c.state === stateFilter)
    : conversations;

  const states = ["active", "completed", "paused", "expired"];

  if (loading) {
    return (
      <div className="flex-1 p-4 space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 rounded-lg bg-slate-100 dark:bg-slate-800 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Filter bar */}
      <div className="px-5 py-2 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setStateFilter(null)}
            className={cn(
              "px-2 py-1 text-xs rounded-full transition-colors",
              !stateFilter
                ? "bg-reclaw-100 text-reclaw-700 dark:bg-reclaw-900/30 dark:text-reclaw-400"
                : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            )}
          >
            All ({conversations.length})
          </button>
          {states.map((s) => {
            const count = conversations.filter((c) => c.state === s).length;
            if (count === 0) return null;
            return (
              <button
                key={s}
                onClick={() => setStateFilter(s)}
                className={cn(
                  "px-2 py-1 text-xs rounded-full transition-colors capitalize",
                  stateFilter === s
                    ? "bg-reclaw-100 text-reclaw-700 dark:bg-reclaw-900/30 dark:text-reclaw-400"
                    : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                )}
              >
                {s} ({count})
              </button>
            );
          })}
        </div>
        <button
          onClick={fetchConversations}
          aria-label="Refresh conversations"
          className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-sm text-slate-500 dark:text-slate-400">No conversations found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800">
                <th className="px-5 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">Participant</th>
                <th className="px-5 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">State</th>
                <th className="px-5 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">Progress</th>
                <th className="px-5 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">Started</th>
                <th className="px-5 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">Last Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.map((conv) => {
                const badge = STATE_BADGE[conv.state] || STATE_BADGE.expired;
                return (
                  <tr key={conv.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <User size={14} className="text-slate-400" />
                        <span className="text-sm text-slate-900 dark:text-white">{conv.participant_name}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", badge.classes)}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <span className="text-sm text-slate-600 dark:text-slate-300">
                        Q{conv.current_question_index + 1}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {new Date(conv.started_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {conv.last_message_at ? new Date(conv.last_message_at).toLocaleString() : "---"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
