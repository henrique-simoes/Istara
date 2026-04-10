"use client";

import { useState, useRef, useEffect } from "react";
import { Send, X, MessageSquare, AlertTriangle, Undo2 } from "lucide-react";
import { steering } from "@/lib/api";
import { cn } from "@/lib/utils";

interface SteeringInputProps {
  agentId: string;
  isWorking: boolean;
  onMessageSent?: () => void;
  className?: string;
}

/**
 * Mid-execution steering input — inspired by pi-mono's message queue pattern.
 *
 * Allows users to inject messages to an agent while it's working.
 * Steering messages are delivered after the current skill execution completes
 * (deferred execution — tools are NEVER interrupted mid-flight).
 *
 * Features:
 * - Steering message queue (Enter to send)
 * - Abort button (cancels current work, clears queues)
 * - Queue count badge (shows pending messages)
 * - Retrieve queued messages (restores to editor)
 */
export default function SteeringInput({
  agentId,
  isWorking,
  onMessageSent,
  className,
}: SteeringInputProps) {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [queueCount, setQueueCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Poll queue count when agent is working
  useEffect(() => {
    if (!agentId || !isWorking) {
      setQueueCount(0);
      return;
    }
    let cancelled = false;
    const poll = async () => {
      try {
        const status = await steering.getStatus(agentId);
        if (!cancelled) {
          setQueueCount(status.steering_queue_count + status.follow_up_queue_count);
        }
      } catch {
        // Ignore polling errors
      }
    };
    poll();
    const interval = setInterval(poll, 3000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [agentId, isWorking]);

  const handleSend = async () => {
    if (!message.trim() || sending) return;
    setSending(true);
    setError(null);
    try {
      await steering.send(agentId, message.trim());
      setMessage("");
      setQueueCount((prev) => prev + 1);
      onMessageSent?.();
      inputRef.current?.focus();
    } catch (err: any) {
      setError(err.message || "Failed to send steering message");
    } finally {
      setSending(false);
    }
  };

  const handleAbort = async () => {
    try {
      await steering.abort(agentId);
      setQueueCount(0);
      setMessage("");
    } catch (err: any) {
      setError(err.message || "Failed to abort");
    }
  };

  const handleRetrieveQueued = () => {
    // Restore queued messages to input
    steering.getQueues(agentId).then((queues) => {
      const allMessages = [...queues.steering_queue, ...queues.follow_up_queue]
        .map((m) => m.message)
        .join("\n");
      if (allMessages) {
        setMessage(allMessages);
        setQueueCount(0);
        inputRef.current?.focus();
      }
    }).catch(() => {});
  };

  if (!isWorking && queueCount === 0) return null;

  return (
    <div className={cn("mt-3 p-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700", className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <MessageSquare size={14} className="text-istara-500" />
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
            {isWorking ? "Agent is working — steering message will be queued" : "Queued steering messages"}
          </span>
          {queueCount > 0 && (
            <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 text-[10px] font-bold text-white bg-istara-500 rounded-full">
              {queueCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {queueCount > 0 && (
            <button
              onClick={handleRetrieveQueued}
              className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              title="Retrieve queued messages"
              aria-label="Retrieve queued steering messages"
            >
              <Undo2 size={12} />
            </button>
          )}
          {isWorking && (
            <button
              onClick={handleAbort}
              className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-slate-400 hover:text-red-500 transition-colors"
              title="Abort current work"
              aria-label="Abort agent's current work"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          value={message}
          onChange={(e) => {
            setMessage(e.target.value);
            if (error) setError(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder={
            isWorking
              ? "Type a message to inject after current task completes..."
              : "Type a follow-up message for when the agent finishes..."
          }
          className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-istara-500 focus:border-transparent"
          aria-label="Steering message input"
        />
        <button
          onClick={handleSend}
          disabled={!message.trim() || sending}
          className={cn(
            "p-2 rounded-lg transition-colors",
            message.trim() && !sending
              ? "bg-istara-600 text-white hover:bg-istara-700"
              : "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed",
          )}
          aria-label="Send steering message"
        >
          {sending ? (
            <div className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
          ) : (
            <Send size={14} />
          )}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mt-2 flex items-center gap-1.5 text-xs text-red-500">
          <AlertTriangle size={10} />
          {error}
        </div>
      )}
    </div>
  );
}
