"use client";

import { useEffect, useState } from "react";
import { Plus, MessageSquare, Filter } from "lucide-react";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { cn } from "@/lib/utils";
import ChannelInstanceCard from "./ChannelInstanceCard";
import ChannelSetupWizard from "./ChannelSetupWizard";
import ChannelMessagesPanel from "./ChannelMessagesPanel";
import ChannelConversationsPanel from "./ChannelConversationsPanel";

const PLATFORMS = [
  { id: null, label: "All" },
  { id: "telegram", label: "Telegram" },
  { id: "slack", label: "Slack" },
  { id: "whatsapp", label: "WhatsApp" },
  { id: "google_chat", label: "Google Chat" },
] as const;

export default function MessagingTab() {
  const {
    channelInstances,
    channelLoading,
    selectedInstanceId,
    fetchChannels,
    selectInstance,
  } = useIntegrationsStore();

  const [platformFilter, setPlatformFilter] = useState<string | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [detailView, setDetailView] = useState<"messages" | "conversations">("messages");

  useEffect(() => {
    fetchChannels(platformFilter || undefined);
  }, [fetchChannels, platformFilter]);

  const selectedInstance = channelInstances.find((c) => c.id === selectedInstanceId);

  if (showWizard) {
    return (
      <ChannelSetupWizard
        onClose={() => {
          setShowWizard(false);
          fetchChannels();
        }}
      />
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left: channel list */}
      <div className="w-80 shrink-0 border-r border-slate-200 dark:border-slate-800 flex flex-col overflow-hidden">
        {/* Filter bar */}
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Channels</h2>
            <button
              onClick={() => setShowWizard(true)}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors"
            >
              <Plus size={12} />
              Add Channel
            </button>
          </div>

          <div className="flex items-center gap-1 overflow-x-auto">
            {PLATFORMS.map((p) => (
              <button
                key={p.id ?? "all"}
                onClick={() => setPlatformFilter(p.id)}
                className={cn(
                  "px-2.5 py-1 text-xs rounded-full whitespace-nowrap transition-colors",
                  platformFilter === p.id
                    ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                    : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                )}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Channel list */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {channelLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-28 rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse" />
            ))
          ) : channelInstances.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare size={32} className="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">No channels configured</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
                Connect a messaging platform to start collecting research data.
              </p>
              <button
                onClick={() => setShowWizard(true)}
                className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors"
              >
                Add First Channel
              </button>
            </div>
          ) : (
            channelInstances.map((instance) => (
              <ChannelInstanceCard
                key={instance.id}
                instance={instance}
                onSelect={selectInstance}
                selected={selectedInstanceId === instance.id}
              />
            ))
          )}
        </div>
      </div>

      {/* Right: detail panel */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {selectedInstance ? (
          <>
            {/* Detail header */}
            <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{selectedInstance.name}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {selectedInstance.platform} &middot; {selectedInstance.message_count} messages
                </p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setDetailView("messages")}
                  className={cn(
                    "px-3 py-1.5 text-xs rounded-lg transition-colors",
                    detailView === "messages"
                      ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                      : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                  )}
                >
                  Messages
                </button>
                <button
                  onClick={() => setDetailView("conversations")}
                  className={cn(
                    "px-3 py-1.5 text-xs rounded-lg transition-colors",
                    detailView === "conversations"
                      ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                      : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                  )}
                >
                  Conversations
                </button>
              </div>
            </div>

            {detailView === "messages" ? (
              <ChannelMessagesPanel channelId={selectedInstance.id} />
            ) : (
              <ChannelConversationsPanel channelId={selectedInstance.id} />
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-center p-8">
            <div>
              <MessageSquare size={40} className="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
              <p className="text-sm text-slate-500 dark:text-slate-400">Select a channel to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
