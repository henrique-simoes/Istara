"use client";

import { useEffect, useState } from "react";
import { X, ArrowLeft, ArrowRight } from "lucide-react";
import { deployments as deploymentsApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface TranscriptMessage {
  id: string;
  role: "interviewer" | "participant" | "system";
  content: string;
  created_at: string;
}

interface ConversationTranscriptProps {
  deploymentId: string;
  conversationId: string;
  onClose: () => void;
}

export default function ConversationTranscript({ deploymentId, conversationId, onClose }: ConversationTranscriptProps) {
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    deploymentsApi.transcript(deploymentId, conversationId)
      .then((data) => {
        setMessages(data.messages || data || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [deploymentId, conversationId]);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* Slide-over panel */}
      <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-800">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Conversation Transcript</h3>
          <button
            onClick={onClose}
            aria-label="Close transcript"
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className={cn("max-w-[80%] h-16 rounded-2xl animate-pulse", i % 2 === 0 ? "bg-slate-100 dark:bg-slate-800 ml-auto" : "bg-slate-100 dark:bg-slate-800")} />
            ))
          ) : messages.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-sm text-slate-500 dark:text-slate-400">No messages in this conversation yet.</p>
            </div>
          ) : (
            messages.map((msg) => {
              const isInterviewer = msg.role === "interviewer" || msg.role === "system";
              return (
                <div key={msg.id} className={cn("flex", isInterviewer ? "justify-start" : "justify-end")}>
                  <div className={cn(
                    "max-w-[80%] px-4 py-2.5 rounded-2xl",
                    isInterviewer
                      ? "bg-slate-100 dark:bg-slate-800 rounded-tl-sm"
                      : "bg-reclaw-500 text-white rounded-tr-sm"
                  )}>
                    <div className="flex items-center gap-2 mb-1">
                      {isInterviewer ? (
                        <ArrowRight size={10} className="text-slate-400" />
                      ) : (
                        <ArrowLeft size={10} className={isInterviewer ? "text-slate-400" : "text-white/60"} />
                      )}
                      <span className={cn(
                        "text-[10px] font-medium uppercase",
                        isInterviewer ? "text-slate-500 dark:text-slate-400" : "text-white/70"
                      )}>
                        {msg.role}
                      </span>
                    </div>
                    <p className={cn(
                      "text-sm",
                      isInterviewer ? "text-slate-900 dark:text-white" : "text-white"
                    )}>
                      {msg.content}
                    </p>
                    <span className={cn(
                      "text-[10px] mt-1 block",
                      isInterviewer ? "text-slate-400 dark:text-slate-500" : "text-white/50"
                    )}>
                      {new Date(msg.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
