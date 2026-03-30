"use client";

import { useEffect, useState, useCallback } from "react";
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  Zap,
  MessageSquareText,
  ClipboardCheck,
} from "lucide-react";
import { codeApplications as codeAppApi } from "@/lib/api";
import type { CodeApplicationType } from "@/lib/types";
import { cn } from "@/lib/utils";

interface CodeReviewQueueProps {
  projectId: string;
}

export default function CodeReviewQueue({ projectId }: CodeReviewQueueProps) {
  const [items, setItems] = useState<CodeApplicationType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [bulkApproving, setBulkApproving] = useState(false);

  const loadPending = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await codeAppApi.pending(projectId);
      setItems(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load pending code applications"
      );
    }
    setLoading(false);
  }, [projectId]);

  useEffect(() => {
    loadPending();
  }, [loadPending]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only apply shortcuts when not in an input/textarea
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT"
      ) {
        return;
      }

      if (items.length === 0) return;

      // 'a' to approve the first pending item
      if (e.key === "a" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        handleReview(items[0].id, "approved");
      }
      // 'r' to reject the first pending item
      if (e.key === "r" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        handleReview(items[0].id, "rejected");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [items]);

  const handleReview = async (
    applicationId: string,
    status: "approved" | "rejected"
  ) => {
    setReviewingId(applicationId);
    try {
      await codeAppApi.review(applicationId, status);
      setItems((prev) => prev.filter((item) => item.id !== applicationId));
    } catch (err) {
      console.error("Failed to review code application:", err);
    }
    setReviewingId(null);
  };

  const handleBulkApprove = async () => {
    setBulkApproving(true);
    try {
      const result = await codeAppApi.bulkApprove(projectId, 0.9);
      // Remove approved items from the local list
      setItems((prev) => prev.filter((item) => item.confidence < 0.9));
      // If the result shows items were approved, we may need to refresh
      if (result.approved_count > 0) {
        await loadPending();
      }
    } catch (err) {
      console.error("Failed to bulk approve:", err);
    }
    setBulkApproving(false);
  };

  const highConfidenceCount = items.filter(
    (item) => item.confidence >= 0.9
  ).length;

  // Loading state
  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto" role="status" aria-live="polite" aria-label="Loading review queue">
        <span className="sr-only">Loading code review queue...</span>
        <div className="p-4 border-b border-slate-200 dark:border-slate-800">
          <div className="h-6 w-48 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
        </div>
        <div className="p-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="border border-slate-200 dark:border-slate-700 rounded-lg p-4"
            >
              <div className="h-4 w-full bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-3" />
              <div className="h-3 w-3/4 bg-slate-100 dark:bg-slate-800 rounded animate-pulse mb-2" />
              <div className="flex gap-2">
                <div className="h-8 w-20 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                <div className="h-8 w-20 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-8" role="alert">
        <div className="text-center">
          <AlertCircle
            size={32}
            className="mx-auto text-red-500 dark:text-red-400 mb-3"
            aria-hidden="true"
          />
          <p className="text-sm text-red-600 dark:text-red-400 font-medium mb-1">
            Failed to load review queue
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
            {error}
          </p>
          <button
            onClick={loadPending}
            aria-label="Retry loading review queue"
            className="text-xs px-3 py-1.5 rounded-md bg-istara-600 text-white hover:bg-istara-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-istara-500 focus-visible:ring-offset-1"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (items.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8" role="status">
        <div className="text-center">
          <ClipboardCheck
            size={32}
            className="mx-auto text-slate-300 dark:text-slate-600 mb-3"
            aria-hidden="true"
          />
          <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
            No codes pending review
          </p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
            All code applications have been reviewed
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto" role="region" aria-label="Code review queue">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <MessageSquareText
              size={18}
              className="text-istara-600 dark:text-istara-400"
              aria-hidden="true"
            />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Code Review Queue
            </h2>
            <span role="status" className="text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 px-2 py-0.5 rounded-full">
              {items.length} pending
            </span>
          </div>

          {/* Bulk approve button */}
          {highConfidenceCount > 0 && (
            <button
              onClick={handleBulkApprove}
              disabled={bulkApproving}
              aria-label={`Bulk approve ${highConfidenceCount} high confidence codes`}
              className={cn(
                "inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md font-medium transition-colors",
                bulkApproving
                  ? "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
                  : "bg-green-600 text-white hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 focus-visible:ring-offset-1"
              )}
            >
              {bulkApproving ? (
                <Loader2 size={12} className="animate-spin" aria-hidden="true" />
              ) : (
                <Zap size={12} aria-hidden="true" />
              )}
              Bulk Approve High Confidence ({highConfidenceCount})
            </button>
          )}
        </div>

        {/* Keyboard shortcut hints */}
        <p className="text-xs text-slate-400 dark:text-slate-500">
          Keyboard shortcuts:{" "}
          <kbd className="px-1 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-[10px] font-mono">
            A
          </kbd>{" "}
          approve first{" "}
          <kbd className="px-1 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-[10px] font-mono">
            R
          </kbd>{" "}
          reject first
        </p>
      </div>

      {/* Review items */}
      <div className="p-4 space-y-3" role="list" aria-label="Pending code applications" aria-live="polite">
        {items.map((item) => {
          const isReviewing = reviewingId === item.id;
          return (
            <div
              key={item.id}
              role="listitem"
              aria-label={`Code application: ${item.code_id}`}
              className={cn(
                "border rounded-lg overflow-hidden transition-opacity",
                isReviewing
                  ? "border-slate-300 dark:border-slate-600 opacity-50"
                  : "border-slate-200 dark:border-slate-700"
              )}
            >
              {/* Source text (highlighted) */}
              <div className="p-4">
                <div className="mb-3">
                  <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                    Source Text
                  </p>
                  <div className="bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-800 rounded-md p-2.5">
                    <p className="text-sm text-slate-900 dark:text-white leading-relaxed">
                      {item.source_text}
                    </p>
                  </div>
                  {item.source_location && (
                    <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                      Source: {item.source_location}
                    </p>
                  )}
                </div>

                {/* Code + Reasoning */}
                <div className="flex items-start gap-4 mb-3">
                  <div className="flex-1">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Applied Code
                    </p>
                    <span className="inline-flex items-center gap-1 text-sm font-medium text-istara-700 dark:text-istara-400 bg-istara-50 dark:bg-istara-900/20 px-2 py-0.5 rounded">
                      {item.code_id}
                    </span>
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Coder
                    </p>
                    <span
                      className={cn(
                        "text-xs px-1.5 py-0.5 rounded",
                        item.coder_type === "llm"
                          ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
                          : item.coder_type === "human"
                            ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                            : "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400"
                      )}
                    >
                      <span className="sr-only">Coder type: </span>
                      {item.coder_type}
                    </span>
                  </div>
                </div>

                {/* Reasoning */}
                {item.reasoning && (
                  <div className="mb-3">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Coding Reasoning
                    </p>
                    <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                      {item.reasoning}
                    </p>
                  </div>
                )}

                {/* Confidence bar */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                      Confidence
                    </p>
                    <span
                      role="status"
                      className={cn(
                        "text-xs font-medium",
                        item.confidence >= 0.9
                          ? "text-green-600 dark:text-green-400"
                          : item.confidence >= 0.7
                            ? "text-yellow-600 dark:text-yellow-400"
                            : "text-red-600 dark:text-red-400"
                      )}
                    >
                      {Math.round(item.confidence * 100)}%
                      <span className="sr-only">
                        {" "}({item.confidence >= 0.9 ? "high" : item.confidence >= 0.7 ? "medium" : "low"} confidence)
                      </span>
                    </span>
                  </div>
                  <div
                    className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden"
                    role="progressbar"
                    aria-valuenow={Math.round(item.confidence * 100)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`Confidence: ${Math.round(item.confidence * 100)}%`}
                  >
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        item.confidence >= 0.9
                          ? "bg-green-500"
                          : item.confidence >= 0.7
                            ? "bg-yellow-500"
                            : "bg-red-500"
                      )}
                      style={{ width: `${Math.round(item.confidence * 100)}%` }}
                    />
                  </div>
                </div>

                {/* Action buttons */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleReview(item.id, "approved")}
                    disabled={isReviewing}
                    aria-label={`Approve code application for ${item.code_id}`}
                    className={cn(
                      "inline-flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-md transition-colors",
                      isReviewing
                        ? "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
                        : "bg-green-600 text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-1"
                    )}
                  >
                    {isReviewing ? (
                      <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                    ) : (
                      <CheckCircle2 size={14} aria-hidden="true" />
                    )}
                    Approve
                  </button>
                  <button
                    onClick={() => handleReview(item.id, "rejected")}
                    disabled={isReviewing}
                    aria-label={`Reject code application for ${item.code_id}`}
                    className={cn(
                      "inline-flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-md transition-colors",
                      isReviewing
                        ? "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
                        : "bg-red-600 text-white hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-1"
                    )}
                  >
                    {isReviewing ? (
                      <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                    ) : (
                      <XCircle size={14} aria-hidden="true" />
                    )}
                    Reject
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
