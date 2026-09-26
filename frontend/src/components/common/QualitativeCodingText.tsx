"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  Check,
  ChevronDown,
  Info,
  Loader2,
  Plus,
  Search,
  Tag,
  Trash2,
  X,
} from "lucide-react";
import { codebookVersions as codebookApi } from "@/lib/api";
import { codeApplications } from "@/lib/researchIntegrityApi";
import type { CodeApplicationType, CodebookVersionType, CodeEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

interface QualitativeCodingTextProps {
  projectId: string;
  sourceDocumentId?: string;
  sourceType?: "document" | "interview";
  text: string;
  className?: string;
  onCodeApplied?: (ca: CodeApplicationType) => void;
  onCodeDeleted?: (id: string) => void;
  taskId?: string;
  readOnly?: boolean;
}

const TAG_PALETTE = [
  { bg: "bg-purple-100 dark:bg-purple-900/40", text: "text-purple-800 dark:text-purple-300", border: "border-purple-300 dark:border-purple-700", ring: "ring-purple-400" },
  { bg: "bg-blue-100 dark:bg-blue-900/40", text: "text-blue-800 dark:text-blue-300", border: "border-blue-300 dark:border-blue-700", ring: "ring-blue-400" },
  { bg: "bg-emerald-100 dark:bg-emerald-900/40", text: "text-emerald-800 dark:text-emerald-300", border: "border-emerald-300 dark:border-emerald-700", ring: "ring-emerald-400" },
  { bg: "bg-amber-100 dark:bg-amber-900/40", text: "text-amber-800 dark:text-amber-300", border: "border-amber-300 dark:border-amber-700", ring: "ring-amber-400" },
  { bg: "bg-rose-100 dark:bg-rose-900/40", text: "text-rose-800 dark:text-rose-300", border: "border-rose-300 dark:border-rose-700", ring: "ring-rose-400" },
  { bg: "bg-teal-100 dark:bg-teal-900/40", text: "text-teal-800 dark:text-teal-300", border: "border-teal-300 dark:border-teal-700", ring: "ring-teal-400" },
  { bg: "bg-indigo-100 dark:bg-indigo-900/40", text: "text-indigo-800 dark:text-indigo-300", border: "border-indigo-300 dark:border-indigo-700", ring: "ring-indigo-400" },
];

function getCodeColor(codeId: string) {
  let hash = 0;
  for (let i = 0; i < codeId.length; i++) {
    hash = (hash << 5) - hash + codeId.charCodeAt(i);
    hash |= 0;
  }
  const index = Math.abs(hash) % TAG_PALETTE.length;
  return TAG_PALETTE[index];
}

export default function QualitativeCodingText({
  projectId,
  sourceDocumentId,
  sourceType = "document",
  text,
  className,
  onCodeApplied,
  onCodeDeleted,
  taskId,
  readOnly = false,
}: QualitativeCodingTextProps) {
  const [codeApps, setCodeApps] = useState<CodeApplicationType[]>([]);
  const [codebooks, setCodebooks] = useState<CodebookVersionType[]>([]);
  const [loading, setLoading] = useState(false);

  // Selection & Popover state
  const [selectionRange, setSelectionRange] = useState<{
    text: string;
    start: number;
    end: number;
    rect: { x: number; y: number };
  } | null>(null);

  // Active inspector popover
  const [inspectingApp, setInspectingApp] = useState<{
    app: CodeApplicationType;
    rect: { x: number; y: number };
  } | null>(null);

  const [showGutter, setShowGutter] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load codebooks & applications
  const loadData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const [apps, cbs] = await Promise.all([
        codeApplications.list(projectId, undefined, taskId, sourceDocumentId),
        codebookApi.list(projectId),
      ]);
      setCodeApps(apps || []);
      setCodebooks(cbs || []);
    } catch (e) {
      console.error("Failed to load qualitative coding data:", e);
    } finally {
      setLoading(false);
    }
  }, [projectId, sourceDocumentId, taskId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

function normalizeCodeEntry(code: any): CodeEntry {
  return {
    code_id: code.code_id || code.id || "code",
    label: code.label || code.name || code.code_id || code.id || "Untitled code",
    brief_definition: code.brief_definition || code.definition || "",
    full_definition: code.full_definition || code.inclusion_criteria || code.definition || "",
    exclusion_criteria: code.exclusion_criteria || "",
    typical_example: code.typical_example || (Array.isArray(code.examples) ? code.examples[0] : "") || "",
    boundary_example: code.boundary_example || (Array.isArray(code.examples) ? code.examples.slice(1).join("\n") : "") || "",
    coding_method: code.coding_method || code.code_type || "descriptive",
    frequency: code.frequency || 0,
    parent_theme: code.parent_theme || code.parent_code_id || null,
  };
}

  // All codes available across versions
  const availableCodes = useMemo(() => {
    const map = new Map<string, { code: CodeEntry; versionId: string; versionNum: string }>();
    codebooks.forEach((cb) => {
      (cb.codes || []).forEach((rawCode: any) => {
        const c = normalizeCodeEntry(rawCode);
        const key = c.label.toLowerCase();
        if (!map.has(key)) {
          map.set(key, {
            code: c,
            versionId: cb.id,
            versionNum: cb.version,
          });
        }
      });
    });
    return Array.from(map.values());
  }, [codebooks]);

  // Handle text selection
  const handleMouseUp = useCallback(() => {
    if (readOnly) return;
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) return;

    const selectedText = sel.toString().trim();
    if (selectedText.length < 2) return;

    // Determine character offsets within full text
    const idx = text.indexOf(selectedText);
    const start = idx >= 0 ? idx : 0;
    const end = idx >= 0 ? idx + selectedText.length : selectedText.length;

    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();

    setSelectionRange({
      text: selectedText,
      start,
      end,
      rect: {
        x: Math.min(Math.max(10, rect.left), window.innerWidth - 320),
        y: rect.bottom + window.scrollY + 6,
      },
    });
    setInspectingApp(null);
  }, [readOnly, text]);

  // Apply code to selection
  const handleApplyCode = async (codeId: string, reasoning: string, codebookVersionId?: string) => {
    if (!selectionRange) return;
    try {
      const newApp = await codeApplications.create(projectId, {
        code_id: codeId,
        codebook_version_id: codebookVersionId || (codebooks[0]?.id ?? null),
        source_document_id: sourceDocumentId || null,
        source_text: selectionRange.text,
        source_type: sourceType,
        start_offset: selectionRange.start,
        end_offset: selectionRange.end,
        task_id: taskId || null,
        reasoning: reasoning || "Coded via Qualitative Coding Studio",
      });

      setCodeApps((prev) => [newApp, ...prev]);
      setSelectionRange(null);
      window.getSelection()?.removeAllRanges();
      onCodeApplied?.(newApp);
    } catch (err) {
      console.error("Failed to apply code:", err);
      alert("Failed to apply code. Please try again.");
    }
  };

  // Delete applied code
  const handleDeleteCode = async (appId: string) => {
    try {
      await codeApplications.delete(appId, projectId);
      setCodeApps((prev) => prev.filter((a) => a.id !== appId));
      setInspectingApp(null);
      onCodeDeleted?.(appId);
    } catch (err) {
      console.error("Failed to delete code application:", err);
      alert("Failed to remove code. Please try again.");
    }
  };

  // Build rendered segments with highlights
  const segments = useMemo(() => {
    if (!text) return [];
    if (codeApps.length === 0) {
      return [{ type: "text" as const, text, key: "text-0" }];
    }

    // Match code applications to occurrences in text
    interface MarkSpan {
      start: number;
      end: number;
      app: CodeApplicationType;
    }

    const marks: MarkSpan[] = [];
    codeApps.forEach((app) => {
      const q = app.source_text.trim();
      if (!q) return;

      if (app.start_offset != null && app.end_offset != null && app.end_offset <= text.length) {
        // Verify snippet matches or use start/end
        marks.push({
          start: app.start_offset,
          end: app.end_offset,
          app,
        });
      } else {
        // Fallback: search occurrence
        const found = text.indexOf(q);
        if (found !== -1) {
          marks.push({
            start: found,
            end: found + q.length,
            app,
          });
        }
      }
    });

    // Sort by start position
    marks.sort((a, b) => a.start - b.start);

    // Build disjoint segments
    const result: Array<{
      type: "text" | "mark";
      text: string;
      app?: CodeApplicationType;
      key: string;
    }> = [];

    let cursor = 0;
    marks.forEach((m, i) => {
      if (m.start < cursor) return; // Skip overlapping for stability
      if (m.start > cursor) {
        result.push({
          type: "text",
          text: text.slice(cursor, m.start),
          key: `text-${cursor}-${m.start}`,
        });
      }
      result.push({
        type: "mark",
        text: text.slice(m.start, m.end),
        app: m.app,
        key: `mark-${m.app.id}-${i}`,
      });
      cursor = m.end;
    });

    if (cursor < text.length) {
      result.push({
        type: "text",
        text: text.slice(cursor),
        key: `text-${cursor}-end`,
      });
    }

    return result;
  }, [codeApps, text]);

  return (
    <div className={cn("relative font-sans", className)}>
      {/* Code applications count badge bar */}
      <div className="flex items-center justify-between py-1.5 px-3 bg-slate-100/70 dark:bg-slate-800/50 rounded-t border-b border-slate-200 dark:border-slate-700 text-xs text-slate-500 mb-2">
        <div className="flex items-center gap-2">
          <Tag size={13} className="text-istara-600 dark:text-istara-400" />
          <span className="font-medium text-slate-700 dark:text-slate-300">
            {codeApps.length} qualitative code{codeApps.length === 1 ? "" : "s"} applied
          </span>
          {loading && <Loader2 size={12} className="animate-spin text-slate-400" />}
        </div>
        <div className="flex items-center gap-3">
          {codeApps.length > 0 && (
            <button
              onClick={() => setShowGutter(!showGutter)}
              className="text-[11px] font-medium text-istara-600 dark:text-istara-400 hover:underline"
            >
              {showGutter ? "Hide Gutter Rail" : "Show Gutter Rail"}
            </button>
          )}
          {!readOnly && (
            <span className="text-[11px] text-slate-400">
              Select any text to apply qualitative codes
            </span>
          )}
        </div>
      </div>

      {/* Rendered content with optional Margin Gutter Rail (below the text on a phone) */}
      <div className="flex flex-col md:flex-row gap-4 items-start">
        <div
          ref={containerRef}
          onMouseUp={handleMouseUp}
          className={cn(
            "whitespace-pre-wrap text-sm leading-relaxed text-slate-800 dark:text-slate-200 select-text cursor-text",
            showGutter && codeApps.length > 0 ? "flex-1 min-w-0" : "w-full"
          )}
        >
          {segments.map((seg) => {
            if (seg.type === "text") {
              return <span key={seg.key}>{seg.text}</span>;
            }
            const app = seg.app!;
            const color = getCodeColor(app.code_id);
            return (
              <mark
                key={seg.key}
                onClick={(e) => {
                  e.stopPropagation();
                  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                  setInspectingApp({
                    app,
                    rect: {
                      x: Math.min(Math.max(10, rect.left), window.innerWidth - 300),
                      y: rect.bottom + window.scrollY + 4,
                    },
                  });
                  setSelectionRange(null);
                }}
                className={cn(
                  "rounded px-1 py-0.5 transition-all cursor-pointer inline-flex items-center gap-1 border mx-0.5",
                  color.bg,
                  color.border,
                  color.text,
                  "hover:ring-2",
                  color.ring
                )}
                title={`Code: ${app.code_id} (Click to inspect or delete)`}
              >
                <span>{seg.text}</span>
                <span className="inline-flex items-center gap-0.5 px-1 rounded text-[10px] font-semibold bg-white/80 dark:bg-slate-900/80 shadow-xs">
                  <Tag size={9} />
                  {app.code_id}
                </span>
              </mark>
            );
          })}
        </div>

        {/* Margin Gutter Brackets & Badges Rail */}
        {showGutter && (
          <aside
            aria-label="Margin Gutter Annotations"
            className="w-full md:w-56 shrink-0 md:border-l border-slate-200 dark:border-slate-800 md:pl-3 space-y-2 select-none overflow-y-auto max-h-[600px]"
          >
            <div className="text-[10px] uppercase font-semibold tracking-wider text-slate-400 mb-2 flex items-center justify-between">
              <span>Gutter Annotations</span>
              <span className="font-mono text-slate-500">({codeApps.length})</span>
            </div>
            {codeApps.length === 0 ? (
              <div className="p-4 text-center border border-dashed border-slate-200 dark:border-slate-800 rounded-lg text-slate-400">
                <Tag size={16} className="mx-auto mb-1 text-slate-300 dark:text-slate-600" />
                <p className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Margin Gutter Rail Active</p>
                <p className="text-[10px] text-slate-400 mt-0.5">Select any text span to attach qualitative codes.</p>
              </div>
            ) : (
              codeApps.map((app) => {
              const color = getCodeColor(app.code_id);
              return (
                <div
                  key={app.id}
                  onClick={() => {
                    setInspectingApp({
                      app,
                      rect: { x: window.innerWidth / 2 - 150, y: 200 },
                    });
                  }}
                  className={cn(
                    "p-2 rounded-md border text-left cursor-pointer transition-all hover:shadow-xs hover:-translate-y-0.5 group",
                    color.bg,
                    color.border
                  )}
                  title="Click to inspect this qualitative annotation"
                >
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className={cn("text-xs font-semibold flex items-center gap-1", color.text)}>
                      <Tag size={10} />
                      {app.code_id}
                    </span>
                    <span className="text-[9px] px-1 py-0.2 rounded bg-white/80 dark:bg-slate-900/80 text-slate-500 font-mono">
                      {app.coder_type || "human"}
                    </span>
                  </div>
                  <p
                    className="text-[11px] text-slate-600 dark:text-slate-300 italic line-clamp-2 font-serif border-l-2 pl-1.5"
                    style={{ borderColor: "currentColor" }}
                  >
                    &ldquo;{app.source_text}&rdquo;
                  </p>
                </div>
              );
            }))}
          </aside>
        )}
      </div>

      {/* Floating Tag Creation Popover */}
      {selectionRange && !readOnly && (
        <FloatingCodingPopover
          position={selectionRange.rect}
          selectedText={selectionRange.text}
          availableCodes={availableCodes}
          onApply={handleApplyCode}
          onClose={() => setSelectionRange(null)}
        />
      )}

      {/* Code Inspector / Delete Popover */}
      {inspectingApp && (
        <CodeInspectorPopover
          position={inspectingApp.rect}
          app={inspectingApp.app}
          onDelete={() => handleDeleteCode(inspectingApp.app.id)}
          onClose={() => setInspectingApp(null)}
          readOnly={readOnly}
        />
      )}
    </div>
  );
}

// ── Floating Coding Popover ──

function FloatingCodingPopover({
  position,
  selectedText,
  availableCodes,
  onApply,
  onClose,
}: {
  position: { x: number; y: number };
  selectedText: string;
  availableCodes: Array<{ code: CodeEntry; versionId: string; versionNum: string }>;
  onApply: (codeId: string, reasoning: string, versionId?: string) => Promise<void>;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState<"pick" | "create">("pick");
  const [search, setSearch] = useState("");
  const [selectedCode, setSelectedCode] = useState<{ id: string; versionId?: string } | null>(null);
  const [newCodeLabel, setNewCodeLabel] = useState("");
  const [reasoning, setReasoning] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [activeTab]);

  const filtered = availableCodes.filter((item) =>
    item.code.label.toLowerCase().includes(search.toLowerCase()) ||
    item.code.brief_definition?.toLowerCase().includes(search.toLowerCase())
  );

  const handleSubmit = async () => {
    let targetCodeId = "";
    let versionId: string | undefined = undefined;

    if (activeTab === "pick") {
      if (!selectedCode) return;
      targetCodeId = selectedCode.id;
      versionId = selectedCode.versionId;
    } else {
      if (!newCodeLabel.trim()) return;
      targetCodeId = newCodeLabel.trim();
    }

    setIsSubmitting(true);
    try {
      await onApply(targetCodeId, reasoning, versionId);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl p-3 w-80 text-left animate-in fade-in zoom-in-95 duration-100"
      style={{ left: position.x, top: position.y }}
      role="dialog"
      aria-label="Tag text with qualitative code"
    >
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center gap-1.5">
          <Tag size={14} className="text-istara-600 dark:text-istara-400" />
          <span className="text-xs font-semibold text-slate-900 dark:text-white">
            Qualitative Coding
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5 rounded"
          aria-label="Close tagging popover"
        >
          <X size={14} />
        </button>
      </div>

      <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-2 italic truncate">
        &ldquo;{selectedText.slice(0, 65)}{selectedText.length > 65 ? "..." : ""}&rdquo;
      </p>

      {/* Tabs */}
      <div className="flex rounded-md bg-slate-100 dark:bg-slate-700/60 p-0.5 mb-2.5 text-xs">
        <button
          type="button"
          onClick={() => setActiveTab("pick")}
          className={cn(
            "flex-1 py-1 rounded text-center font-medium transition-colors",
            activeTab === "pick"
              ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-xs"
              : "text-slate-600 dark:text-slate-400 hover:text-slate-900"
          )}
        >
          Select Existing
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("create")}
          className={cn(
            "flex-1 py-1 rounded text-center font-medium transition-colors",
            activeTab === "create"
              ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-xs"
              : "text-slate-600 dark:text-slate-400 hover:text-slate-900"
          )}
        >
          New Code
        </button>
      </div>

      {activeTab === "pick" ? (
        <div className="space-y-2 mb-3">
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              ref={inputRef}
              type="text"
              placeholder="Filter codebook..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-2.5 py-1 text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-istara-500"
            />
          </div>

          <div className="max-h-36 overflow-y-auto space-y-1 pr-1">
            {filtered.length === 0 ? (
              <p className="text-[11px] text-slate-400 py-3 text-center">
                No matching codes. Switch to &quot;New Code&quot; to create one.
              </p>
            ) : (
              filtered.map(({ code, versionId, versionNum }) => {
                const isSelected = selectedCode?.id === code.label;
                return (
                  <button
                    key={`${versionId}-${code.label}`}
                    type="button"
                    onClick={() => setSelectedCode({ id: code.label, versionId })}
                    className={cn(
                      "w-full flex items-center justify-between p-1.5 rounded text-left text-xs transition-colors border",
                      isSelected
                        ? "bg-istara-50 dark:bg-istara-950/40 border-istara-400 text-istara-900 dark:text-istara-200 font-medium"
                        : "border-transparent hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-300"
                    )}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium">{code.label}</div>
                      {code.brief_definition && (
                        <div className="text-[10px] text-slate-400 truncate">{code.brief_definition}</div>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400 ml-1 shrink-0">v{versionNum}</span>
                    {isSelected && <Check size={12} className="text-istara-600 ml-1 shrink-0" />}
                  </button>
                );
              })
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-2 mb-3">
          <input
            ref={inputRef}
            type="text"
            placeholder="New code name (e.g. Frustration with onboarding)"
            value={newCodeLabel}
            onChange={(e) => setNewCodeLabel(e.target.value)}
            className="w-full px-2.5 py-1.5 text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-istara-500"
          />
        </div>
      )}

      <div className="mb-3">
        <input
          type="text"
          placeholder="Memo / Rationale (optional justification)"
          value={reasoning}
          onChange={(e) => setReasoning(e.target.value)}
          className="w-full px-2.5 py-1 text-[11px] bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-istara-500"
        />
      </div>

      <button
        onClick={handleSubmit}
        disabled={isSubmitting || (activeTab === "pick" ? !selectedCode : !newCodeLabel.trim())}
        className="w-full py-1.5 px-3 rounded-md bg-istara-600 text-white font-medium text-xs hover:bg-istara-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5 transition-colors shadow-sm"
      >
        {isSubmitting ? (
          <>
            <Loader2 size={12} className="animate-spin" /> Applying...
          </>
        ) : (
          <>
            <Check size={12} /> Apply Code to Selection
          </>
        )}
      </button>
    </div>
  );
}

// ── Code Inspector Popover ──

function CodeInspectorPopover({
  position,
  app,
  onDelete,
  onClose,
  readOnly,
}: {
  position: { x: number; y: number };
  app: CodeApplicationType;
  onDelete: () => Promise<void>;
  onClose: () => void;
  readOnly?: boolean;
}) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete();
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div
      className="fixed z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl p-3 w-72 text-left animate-in fade-in zoom-in-95 duration-100"
      style={{ left: position.x, top: position.y }}
      role="dialog"
      aria-label="Code inspection details"
    >
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center gap-1.5">
          <Tag size={13} className="text-istara-600 dark:text-istara-400" />
          <span className="text-xs font-semibold text-slate-900 dark:text-white truncate">
            {app.code_id}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5 rounded"
          aria-label="Close code inspector"
        >
          <X size={14} />
        </button>
      </div>

      <div className="space-y-1.5 text-xs text-slate-600 dark:text-slate-300 mb-3">
        <p className="text-[11px] text-slate-500 dark:text-slate-400 italic bg-slate-50 dark:bg-slate-900/60 p-2 rounded border border-slate-100 dark:border-slate-800">
          &ldquo;{app.source_text}&rdquo;
        </p>
        <div className="flex justify-between text-[11px]">
          <span className="text-slate-400">Coder:</span>
          <span className="font-medium text-slate-700 dark:text-slate-300 capitalize">{app.coder_type} ({app.coder_id || "Researcher"})</span>
        </div>
        <div className="flex justify-between text-[11px]">
          <span className="text-slate-400">Status:</span>
          <span className="font-medium text-emerald-600 dark:text-emerald-400">Reconciled / Accepted</span>
        </div>
        {app.reasoning && (
          <div className="text-[11px] pt-1">
            <span className="text-slate-400 block mb-0.5">Rationale:</span>
            <span className="text-slate-600 dark:text-slate-300">{app.reasoning}</span>
          </div>
        )}
      </div>

      {!readOnly && (
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="w-full py-1 px-2 text-xs font-medium text-red-600 hover:text-white hover:bg-red-600 border border-red-200 dark:border-red-800/60 rounded transition-colors flex items-center justify-center gap-1"
        >
          {isDeleting ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
          Remove Code Application
        </button>
      )}
    </div>
  );
}
