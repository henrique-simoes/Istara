"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Palette, User, Mic } from "lucide-react";
import { useInterfacesStore } from "@/stores/interfacesStore";
import { useProjectStore } from "@/stores/projectStore";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import { cn, formatDate } from "@/lib/utils";

function UserAvatar() {
  return (
    <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center flex-shrink-0">
      <User size={16} className="text-slate-500 dark:text-slate-400" />
    </div>
  );
}

function DesignAvatar() {
  return (
    <div className="w-8 h-8 rounded-full bg-violet-100 dark:bg-violet-900/40 flex items-center justify-center flex-shrink-0" title="Design Lead">
      <Palette size={16} className="text-violet-600 dark:text-violet-400" />
    </div>
  );
}

export default function DesignChatTab() {
  const { designMessages, designStreaming, designStreamingContent, error, sendDesignMessage, fetchDesignHistory } = useInterfacesStore();
  const { activeProjectId } = useProjectStore();
  const { isRecording, isTranscribing, startRecording, stopRecording, cancelRecording, error: voiceError } = useVoiceRecorder();
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasFetchedRef = useRef(false);

  // Fetch design chat history on mount
  useEffect(() => {
    if (activeProjectId && !hasFetchedRef.current) {
      hasFetchedRef.current = true;
      fetchDesignHistory(activeProjectId);
    }
  }, [activeProjectId, fetchDesignHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [designMessages, designStreamingContent]);

  const handleSend = () => {
    if (!input.trim() || !activeProjectId || designStreaming) return;
    sendDesignMessage(activeProjectId, input.trim());
    setInput("");
  };

  const handleVoiceToggle = async () => {
    if (isRecording) {
      const transcribedText = await stopRecording();
      if (transcribedText) {
        setInput((prev) => (prev ? `${prev} ${transcribedText}` : transcribedText));
      }
    } else {
      await startRecording();
    }
  };

  /** Dispatch a toast notification — WCAG 2.2 4.1.3 Status Messages */
  const dispatchToast = (type: "success" | "warning" | "info" | "agent" | "file", title: string, message: string) => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("istara:toast", { detail: { type, title, message } }));
    }
  };

  useEffect(() => {
    if (voiceError) {
      dispatchToast("warning", "Voice Error", voiceError);
    }
  }, [voiceError]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" role="log" aria-label="Design chat messages">
        {designMessages.length === 0 && !designStreaming && (
          <div className="flex items-center justify-center h-full text-slate-400">
            <div className="text-center max-w-md">
              <Palette size={40} className="mx-auto mb-4 text-violet-400" />
              <p className="text-lg mb-2">Design Chat</p>
              <p className="text-sm">
                Ask about design decisions, generate screens, or discuss UI patterns...
              </p>
            </div>
          </div>
        )}

        {designMessages.map((msg: any) => (
          <div
            key={msg.id}
            className={cn(
              "max-w-3xl flex gap-2.5",
              msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
            )}
          >
            <div className="mt-1">
              {msg.role === "user" ? <UserAvatar /> : <DesignAvatar />}
            </div>
            <div className="flex-1 min-w-0">
              {msg.role !== "user" && (
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-1 px-1 font-medium">
                  {msg.agent_name || "Design Lead"}
                </p>
              )}
              <div
                className={cn(
                  "rounded-2xl px-4 py-3",
                  msg.role === "user"
                    ? "bg-istara-600 text-white rounded-br-md"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-bl-md"
                )}
              >
                <div className="whitespace-pre-wrap text-sm">{msg.content}</div>
              </div>
              <p className="text-xs text-slate-400 mt-1 px-1">
                {formatDate(msg.created_at)}
              </p>
            </div>
          </div>
        ))}

        {/* Streaming response */}
        {designStreaming && designStreamingContent && (
          <div className="mr-auto max-w-3xl flex gap-2.5">
            <div className="mt-1"><DesignAvatar /></div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-1 px-1 font-medium">Design Lead</p>
              <div className="rounded-2xl rounded-bl-md px-4 py-3 bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100">
                <div className="whitespace-pre-wrap text-sm streaming-cursor">
                  {designStreamingContent}
                </div>
              </div>
            </div>
          </div>
        )}

        {designStreaming && !designStreamingContent && (
          <div className="mr-auto flex items-center gap-2.5 text-slate-400 px-4">
            <DesignAvatar />
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">Thinking...</span>
          </div>
        )}

        {error && (
          <div className="mr-auto max-w-3xl">
            <div className="rounded-2xl px-4 py-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
              {error}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-end gap-2 max-w-3xl mx-auto">
          <div className="flex-1 relative">
            <textarea
              value={isRecording ? "Recording voice..." : isTranscribing ? "Transcribing..." : input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isRecording || isTranscribing}
              placeholder="Ask about design decisions, generate screens, or discuss UI patterns..."
              rows={1}
              className={cn(
                "w-full resize-none rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-istara-500 focus:border-transparent",
                (isRecording || isTranscribing) && "italic text-slate-500 bg-slate-50 dark:bg-slate-900"
              )}
              style={{ minHeight: "44px", maxHeight: "120px" }}
            />
            {isRecording && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <button 
                  onClick={cancelRecording}
                  className="text-xs text-slate-400 hover:text-red-500"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>

          {/* Voice recording button */}
          <button
            onClick={handleVoiceToggle}
            disabled={designStreaming || isTranscribing}
            aria-label={isRecording ? "Stop recording" : "Start recording"}
            className={cn(
              "p-2.5 rounded-lg transition-colors",
              isRecording 
                ? "bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400 animate-pulse"
                : isTranscribing
                ? "bg-slate-100 dark:bg-slate-800 text-slate-300 cursor-not-allowed"
                : !designStreaming
                ? "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600"
                : "bg-slate-100 dark:bg-slate-800 text-slate-300 cursor-not-allowed"
            )}
            title={isRecording ? "Stop and Transcribe" : "Voice input"}
          >
            {isTranscribing ? <Loader2 size={20} className="animate-spin" /> : <Mic size={20} />}
          </button>

          <button
            onClick={handleSend}
            disabled={!input.trim() || designStreaming}
            aria-label="Send message"
            className={cn(
              "p-2.5 rounded-lg transition-colors",
              input.trim() && !designStreaming
                ? "bg-istara-600 text-white hover:bg-istara-700"
                : "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
            )}
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}
