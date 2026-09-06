"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BookOpen,
  FileText,
  Loader2,
  Quote,
  Search,
  Tag,
  User,
  X,
} from "lucide-react";
import { codeApplications } from "@/lib/researchIntegrityApi";
import { documents as documentsApi } from "@/lib/api";
import type { CodeApplicationType, CodeEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

interface CodeQuotesModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  code: CodeEntry | null;
}

export default function CodeQuotesModal({
  isOpen,
  onClose,
  projectId,
  code,
}: CodeQuotesModalProps) {
  const [quotes, setQuotes] = useState<CodeApplicationType[]>([]);
  const [loading, setLoading] = useState(false);
  const [docMap, setDocMap] = useState<Record<string, string>>({});
  const [filterQuery, setFilterQuery] = useState("");

  const loadQuotes = useCallback(async () => {
    if (!projectId || !code) return;
    setLoading(true);
    try {
      const [apps, docsRes] = await Promise.all([
        codeApplications.list(projectId, undefined, undefined, undefined, code.code_id),
        documentsApi.list({ project_id: projectId, page_size: 200 }).catch(() => ({ documents: [] })),
      ]);
      setQuotes(apps || []);

      const mapping: Record<string, string> = {};
      (docsRes.documents || []).forEach((d: any) => {
        mapping[d.id] = d.name || d.file_name || d.id;
      });
      setDocMap(mapping);
    } catch (e) {
      console.error("Failed to load quotes for code:", e);
    } finally {
      setLoading(false);
    }
  }, [projectId, code]);

  useEffect(() => {
    if (isOpen && code) {
      loadQuotes();
      setFilterQuery("");
    }
  }, [isOpen, code, loadQuotes]);

  if (!isOpen || !code) return null;

  const filteredQuotes = quotes.filter((q) => {
    if (!filterQuery) return true;
    const qLower = filterQuery.toLowerCase();
    const docName = docMap[q.source_document_id || ""] || "";
    return (
      q.source_text.toLowerCase().includes(qLower) ||
      (q.reasoning && q.reasoning.toLowerCase().includes(qLower)) ||
      docName.toLowerCase().includes(qLower) ||
      (q.coder_id && q.coder_id.toLowerCase().includes(qLower))
    );
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="code-quotes-title"
    >
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-istara-50 dark:bg-istara-950/40 text-istara-600 dark:text-istara-400">
              <Quote size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="code-quotes-title" className="text-base font-semibold text-slate-900 dark:text-white">
                  {code.label}
                </h2>
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                  {code.coding_method}
                </span>
                {code.parent_theme && (
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300">
                    Theme: {code.parent_theme}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">
                {code.brief_definition || "All qualitative evidence quotes tagged with this code across the project"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Filter bar */}
        <div className="px-6 py-2.5 bg-slate-50/50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search tagged quotes or source documents..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-istara-500"
            />
          </div>
          <span className="text-xs text-slate-500 shrink-0">
            {filteredQuotes.length} quote{filteredQuotes.length === 1 ? "" : "s"} found
          </span>
        </div>

        {/* Quotes list */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Loader2 size={24} className="animate-spin text-istara-500 mb-2" />
              <p className="text-xs">Loading tagged quotes...</p>
            </div>
          ) : filteredQuotes.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl p-6">
              <Quote size={32} className="mx-auto text-slate-300 dark:text-slate-600 mb-2" />
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {filterQuery ? "No quotes match your filter" : "No quotes tagged yet"}
              </p>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                {filterQuery
                  ? "Try clearing the search query to view all applications."
                  : "Highlight any excerpt in Documents or Interviews to apply this code and trace it through the Research Spine."}
              </p>
            </div>
          ) : (
            filteredQuotes.map((q) => {
              const docName = docMap[q.source_document_id || ""] || q.source_document_id || "Direct Transcript Span";
              return (
                <div
                  key={q.id}
                  className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 p-4 space-y-2 hover:border-istara-300 dark:hover:border-istara-700 transition-colors shadow-2xs"
                >
                  {/* Quote text */}
                  <div className="flex items-start gap-2">
                    <Quote size={14} className="text-istara-500 shrink-0 mt-0.5 rotate-180" />
                    <p className="text-sm text-slate-800 dark:text-slate-100 italic leading-relaxed font-serif">
                      &ldquo;{q.source_text}&rdquo;
                    </p>
                  </div>

                  {/* Rationale / notes */}
                  {q.reasoning && (
                    <p className="text-xs text-slate-500 dark:text-slate-400 pl-6">
                      <span className="font-semibold text-slate-600 dark:text-slate-300">Note: </span>
                      {q.reasoning}
                    </p>
                  )}

                  {/* Metadata footer */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-700/60 text-[11px] text-slate-400">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1 font-medium text-slate-600 dark:text-slate-300">
                        <FileText size={11} />
                        {docName}
                      </span>
                      <span className="flex items-center gap-1">
                        <User size={11} />
                        {q.coder_id || "human"} ({q.coder_type || "human"})
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                        {q.reconciliation_status || "reconciled"}
                      </span>
                      <span>
                        {new Date(q.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium rounded-lg bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-800 dark:text-white transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
