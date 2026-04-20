"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { X, Send, Loader2, ExternalLink, StopCircle } from "lucide-react";
import { chat as chatApi, sessions as sessionsApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface InteractiveSuggestionBoxProps {
  /** Active project ID (required for session creation). */
  projectId: string;
  /** Initial prompt sent to the AI. */
  prompt: string;
  /** Display title for the suggestion box header. */
  title: string;
  /** Called when the user closes the box. */
  onClose: () => void;
  /** Called once a session is created (optional, for parent tracking). */
  onSessionCreated?: (sessionId: string) => void;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function InteractiveSuggestionBox({
  projectId,
  prompt,
  title,
  onClose,
  onSessionCreated,
}: InteractiveSuggestionBoxProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [replyInput, setReplyInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const contentEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const initializedRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom as content streams in
  const scrollToBottom = useCallback(() => {
    contentEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Stream a message to the AI and accumulate the response
  const streamMessage = useCallback(
    async (sid: string, content: string, isInitial: boolean) => {
      setStreaming(true);
      setError(null);

      if (!isInitial) {
        setMessages((prev) => [...prev, { role: "user", content }]);
      }

      // Add a placeholder assistant message
      const assistantIdx = isInitial ? 0 : -1; // Will append
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      try {
        let accumulated = "";
        abortControllerRef.current = new AbortController();
        
        for await (const event of chatApi.send(projectId, content, sid)) {
          if (event.type === "chunk" && event.content) {
            accumulated += event.content;
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = { role: "assistant", content: accumulated };
              return updated;
            });
          }
        }
      } catch (e: any) {
        if (e.name !== "AbortError" && e.message !== "aborted") {
          setError(e.message || "Failed to get AI response");
        }
      }

      setStreaming(false);
    },
    [projectId]
  );

  // Stop streaming
  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setStreaming(false);
  }, []);

  // Initialize: create session and send the initial prompt
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    (async () => {
      try {
        setStreaming(true);
        const session = await sessionsApi.create({
          project_id: projectId,
          title: `Suggestion: ${title}`,
        });
        setSessionId(session.id);
        onSessionCreated?.(session.id);
        await streamMessage(session.id, prompt, true);
      } catch (e: any) {
        setError(e.message || "Failed to create suggestion session");
        setStreaming(false);
      }
    })();
  }, [projectId, prompt, title, onSessionCreated, streamMessage]);

  // Handle quick reply
  const handleReply = useCallback(async () => {
    const text = replyInput.trim();
    if (!text || !sessionId || streaming) return;
    setReplyInput("");
    await streamMessage(sessionId, text, false);
    inputRef.current?.focus();
  }, [replyInput, sessionId, streaming, streamMessage]);

  // Navigate to chat with this session
  const navigateToChat = useCallback(() => {
    if (!sessionId) return;
    window.dispatchEvent(
      new CustomEvent("istara:navigate", {
        detail: { view: "chat", session_id: sessionId },
      })
    );
  }, [sessionId]);

  return (
    <div
      role="region"
      aria-label={`AI Suggestion: ${title}`}
      className="rounded-lg border border-istara-200 dark:border-istara-800 bg-istara-50 dark:bg-istara-900/20 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-istara-200 dark:border-istara-800 bg-istara-100/50 dark:bg-istara-900/40">
        <span className="text-xs font-medium text-istara-700 dark:text-istara-400">{title}</span>
        <div className="flex items-center gap-2">
          {sessionId && !streaming && (
            <button
              onClick={navigateToChat}
              className="flex items-center gap-1 text-xs text-istara-600 dark:text-istara-400 hover:text-istara-800 dark:hover:text-istara-200 transition-colors"
              aria-label="Continue this conversation in Chat"
            >
              Continue in Chat
              <ExternalLink size={12} />
            </button>
          )}
          {streaming && (
            <button
              onClick={stopStreaming}
              className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 px-2 py-0.5 rounded transition-colors"
              aria-label="Stop streaming"
            >
              <StopCircle size={12} />
              Stop
            </button>
          )}
          <button
            onClick={onClose}
            className="p-0.5 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
            aria-label="Close suggestions"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Scrollable message content */}
      <div
        className="max-h-72 overflow-y-auto px-4 py-3 space-y-3"
        role="log"
        aria-live="polite"
        aria-label="Suggestion conversation"
      >
        {messages.map((msg, i) => (
          <div key={i} className={cn("text-sm", msg.role === "user" ? "text-istara-700 dark:text-istara-300 font-medium" : "text-slate-700 dark:text-slate-300")}>
            {msg.role === "user" && (
              <span className="text-[10px] uppercase tracking-wider text-istara-500 dark:text-istara-500 block mb-0.5">You</span>
            )}
            <div className="whitespace-pre-wrap">{msg.content}</div>
          </div>
        ))}
        {streaming && messages.length > 0 && messages[messages.length - 1].content === "" && (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 size={14} className="animate-spin" />
            <span>Thinking...</span>
          </div>
        )}
        {error && (
          <div className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded px-2 py-1">
            {error}
          </div>
        )}
        <div ref={contentEndRef} />
      </div>

      {/* Quick reply input */}
      <div className="border-t border-istara-200 dark:border-istara-800 px-3 py-2">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            value={replyInput}
            onChange={(e) => setReplyInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleReply();
              }
            }}
            placeholder="Ask a follow-up..."
            aria-label="Follow-up question"
            className="flex-1 text-sm px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-istara-500 focus:border-transparent disabled:opacity-50"
            disabled={streaming || !sessionId}
          />
          <button
            onClick={handleReply}
            disabled={streaming || !replyInput.trim() || !sessionId}
            className="p-1.5 rounded-lg bg-istara-600 text-white hover:bg-istara-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            aria-label="Send follow-up"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}