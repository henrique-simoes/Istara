"use client";

import { useEffect, useState } from "react";
import { ArrowRight, ArrowLeft, RefreshCw } from "lucide-react";
import { channels as channelsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChannelMessage } from "@/lib/types";

interface ChannelMessagesPanelProps {
  channelId: string;
}

export default function ChannelMessagesPanel({ channelId }: ChannelMessagesPanelProps) {
  const [messages, setMessages] = useState<ChannelMessage[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchMessages = async () => {
    setLoading(true);
    try {
      const data = await channelsApi.messages(channelId);
      setMessages(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, [channelId]);

  if (loading) {
    return (
      <div className="flex-1 p-4 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 rounded-lg bg-slate-100 dark:bg-slate-800 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="px-5 py-2 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <span className="text-xs text-slate-500 dark:text-slate-400">{messages.length} messages</span>
        <button
          onClick={fetchMessages}
          aria-label="Refresh messages"
          className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Messages list */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-sm text-slate-500 dark:text-slate-400">No messages yet</p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Messages will appear here as they are sent and received.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {messages.map((msg) => (
              <div key={msg.id} className="px-5 py-3 flex items-start gap-3">
                <div className={cn(
                  "mt-1 shrink-0",
                  msg.direction === "outbound" ? "text-reclaw-500" : "text-blue-500"
                )}>
                  {msg.direction === "outbound" ? <ArrowRight size={14} /> : <ArrowLeft size={14} />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                      {msg.sender_name}
                    </span>
                    <span className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded-full",
                      msg.direction === "outbound"
                        ? "bg-reclaw-50 text-reclaw-600 dark:bg-reclaw-900/20 dark:text-reclaw-400"
                        : "bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400"
                    )}>
                      {msg.direction}
                    </span>
                    {msg.content_type !== "text" && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500">
                        {msg.content_type}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-900 dark:text-white break-words">{msg.content}</p>
                  <span className="text-[10px] text-slate-400 dark:text-slate-500 mt-1 block">
                    {new Date(msg.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
