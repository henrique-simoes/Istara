"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowRight, ArrowLeft, RefreshCw, Send, User, Bot, Loader2, Sparkles } from "lucide-react";
import { channels as channelsApi } from "@/lib/api";
import { post } from "@/lib/apiClient";
import { cn } from "@/lib/utils";
import type { ChannelMessage } from "@/lib/types";

interface ChannelMessagesPanelProps {
  channelId: string;
  projectId: string;
}

export default function ChannelMessagesPanel({ channelId, projectId }: ChannelMessagesPanelProps) {
  const [messages, setMessages] = useState<ChannelMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [inputText, setInputText] = useState("");
  const [senderName, setSenderName] = useState("Participant #1");
  const [sending, setSending] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const fetchMessages = useCallback(async () => {
    setLoading(true);
    try {
      const data = await channelsApi.messages(channelId, projectId);
      setMessages(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [channelId, projectId]);

  const handleSendOutbound = async () => {
    if (!inputText.trim() || sending) return;
    setSending(true);
    setStatusMessage(null);
    try {
      await channelsApi.send(channelId, { channel_id: channelId, text: inputText.trim() }, projectId);
      setInputText("");
      setStatusMessage("Outbound message sent successfully.");
      await fetchMessages();
    } catch (e: any) {
      setStatusMessage(`Failed to send: ${e.message}`);
    } finally {
      setSending(false);
    }
  };

  const handleSimulateInbound = async (customText?: string) => {
    const textToSend = (customText || inputText).trim();
    if (!textToSend || sending) return;
    setSending(true);
    setStatusMessage(null);
    try {
      const res = await post<any>(`/api/channels/${channelId}/simulate-inbound?project_id=${encodeURIComponent(projectId)}`, {
        sender_id: `participant-${senderName.toLowerCase().replace(/\s+/g, "-")}`,
        sender_name: senderName,
        text: textToSend,
      });
      if (!customText) setInputText("");
      setStatusMessage(res.reply ? `Inbound processed! Agent reply: "${res.reply.slice(0, 60)}..."` : "Inbound participant message processed.");
      await fetchMessages();
    } catch (e: any) {
      setStatusMessage(`Failed to simulate inbound: ${e.message}`);
    } finally {
      setSending(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

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
                  msg.direction === "outbound" ? "text-istara-500" : "text-blue-500"
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
                        ? "bg-istara-50 text-istara-600 dark:bg-istara-900/20 dark:text-istara-400"
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

      {/* Interactive Message Composer & Participant Inbound Simulator */}
      <div className="p-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/70 space-y-2">
        {statusMessage && (
          <div className="text-xs px-2.5 py-1 rounded bg-istara-50 text-istara-700 dark:bg-istara-950/40 dark:text-istara-300 flex items-center justify-between">
            <span>{statusMessage}</span>
            <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-slate-600">×</button>
          </div>
        )}

        {/* Quick simulation pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto text-[11px] pb-1">
          <span className="text-slate-400 shrink-0 flex items-center gap-0.5">
            <Sparkles size={11} /> Quick Prompts:
          </span>
          {[
            "Notifications are too frequent during work hours.",
            "The medication tracking schedule was easy to navigate.",
            "Can I invite another family caregiver?",
          ].map((preset, idx) => (
            <button
              key={idx}
              onClick={() => handleSimulateInbound(preset)}
              disabled={sending}
              className="px-2 py-0.5 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-istara-400 hover:text-istara-600 dark:hover:text-istara-400 whitespace-nowrap transition-colors disabled:opacity-50"
            >
              {preset.slice(0, 30)}...
            </button>
          ))}
        </div>

        {/* Composer form */}
        <div className="flex flex-col sm:flex-row items-center gap-2">
          <div className="w-full sm:w-36 shrink-0">
            <input
              type="text"
              placeholder="Sender Name"
              value={senderName}
              onChange={(e) => setSenderName(e.target.value)}
              className="w-full px-2.5 py-1.5 text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-istara-500"
            />
          </div>
          <div className="flex-1 w-full relative">
            <input
              type="text"
              placeholder="Type message to send or simulate..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSimulateInbound();
                }
              }}
              className="w-full pl-3 pr-2 py-1.5 text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-istara-500"
            />
          </div>
          <div className="flex items-center gap-1.5 w-full sm:w-auto justify-end">
            <button
              onClick={() => handleSimulateInbound()}
              disabled={sending || !inputText.trim()}
              title="Simulate inbound message from participant"
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors disabled:opacity-50"
            >
              {sending ? <Loader2 size={12} className="animate-spin" /> : <User size={12} />}
              Simulate Inbound
            </button>
            <button
              onClick={handleSendOutbound}
              disabled={sending || !inputText.trim()}
              title="Send outbound system message"
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-istara-600 hover:bg-istara-700 text-white transition-colors disabled:opacity-50"
            >
              <Send size={12} />
              Outbound
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
