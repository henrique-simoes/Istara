"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import {
  FileText,
  Search,
  Filter,
  X,
  ChevronDown,
  RefreshCw,
  Tag,
  Clock,
  Bot,
  Wand2,
  LayoutDashboard,
  Eye,
  Trash2,
  Diamond,
  ArrowLeft,
  FileImage,
  FileAudio,
  FileVideo,
  File,
  FolderInput,
  CheckCircle,
  AlertCircle,
  Loader2,
  ChevronRight,
  PanelRightClose,
  PanelRight,
  List,
  LayoutGrid,
  AlignJustify,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { useDocumentStore } from "@/stores/documentStore";
import { documents as documentsApi, chat as chatApi } from "@/lib/api";
import { cn, phaseLabel } from "@/lib/utils";
import type { ReclawDocument, DocumentContent } from "@/lib/types";
import ViewOnboarding from "@/components/common/ViewOnboarding";

const PHASES = [
  { id: "", label: "All Phases" },
  { id: "discover", label: "Discover" },
  { id: "define", label: "Define" },
  { id: "develop", label: "Develop" },
  { id: "deliver", label: "Deliver" },
];

const SOURCES = [
  { id: "", label: "All Sources" },
  { id: "user_upload", label: "User Upload" },
  { id: "agent_output", label: "Agent Output" },
  { id: "task_output", label: "Task Output" },
  { id: "project_file", label: "Project File" },
  { id: "external", label: "External" },
];

const STATUS_COLORS: Record<string, string> = {
  ready: "text-green-600 bg-green-50 dark:bg-green-900/20",
  processing: "text-blue-600 bg-blue-50 dark:bg-blue-900/20",
  pending: "text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20",
  error: "text-red-600 bg-red-50 dark:bg-red-900/20",
};

const SOURCE_LABELS: Record<string, string> = {
  user_upload: "User Upload",
  agent_output: "Agent Output",
  task_output: "Task Output",
  project_file: "Project File",
  external: "External",
};

function fileIcon(type: string) {
  if ([".jpg", ".jpeg", ".png", ".gif", ".webp"].includes(type)) return FileImage;
  if ([".mp3", ".wav", ".m4a", ".ogg"].includes(type)) return FileAudio;
  if ([".mp4", ".webm", ".mov"].includes(type)) return FileVideo;
  if ([".pdf", ".docx", ".txt", ".md", ".csv"].includes(type)) return FileText;
  return File;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function timeAgo(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return d.toLocaleDateString();
}

export default function DocumentsView() {
  const { activeProjectId } = useProjectStore();
  const {
    documents,
    tags,
    stats,
    loading,
    total,
    page,
    totalPages,
    searchQuery,
    filterPhase,
    filterTag,
    filterSource,
    selectedDocId,
    fetchDocuments,
    fetchTags,
    fetchStats,
    syncDocuments,
    setSearchQuery,
    setFilterPhase,
    setFilterTag,
    setFilterSource,
    selectDocument,
    deleteDocument,
  } = useDocumentStore();

  const [showFilters, setShowFilters] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [organizing, setOrganizing] = useState(false);
  const [organizeResult, setOrganizeResult] = useState("");
  const [previewDoc, setPreviewDoc] = useState<ReclawDocument | null>(null);
  const [previewContent, setPreviewContent] = useState<DocumentContent | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"compact" | "list" | "grid">(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("istara_documents_view_mode");
      if (stored === "compact" || stored === "list" || stored === "grid") return stored;
    }
    return "compact";
  });

  const handleViewMode = useCallback((mode: "compact" | "list" | "grid") => {
    setViewMode(mode);
    localStorage.setItem("istara_documents_view_mode", mode);
  }, []);

  // Fetch documents on project change
  useEffect(() => {
    if (activeProjectId) {
      fetchDocuments(activeProjectId);
      fetchTags(activeProjectId);
      fetchStats(activeProjectId);
      // Auto-sync on load to pick up new project files
      syncDocuments(activeProjectId);
    }
  }, [activeProjectId, fetchDocuments, fetchTags, fetchStats, syncDocuments]);

  // Refetch when filters change
  useEffect(() => {
    if (activeProjectId) {
      fetchDocuments(activeProjectId);
    }
  }, [searchQuery, filterPhase, filterTag, filterSource, activeProjectId, fetchDocuments]);

  const handleSync = async () => {
    if (!activeProjectId) return;
    setSyncing(true);
    await syncDocuments(activeProjectId);
    await fetchDocuments(activeProjectId);
    await fetchTags(activeProjectId);
    await fetchStats(activeProjectId);
    setSyncing(false);
  };

  const handleOrganize = async () => {
    if (!activeProjectId) return;
    setOrganizing(true);
    setOrganizeResult("");
    try {
      let result = "";
      for await (const event of chatApi.send(
        activeProjectId,
        "Organize and categorize all documents in this project by type, topic, and research phase. " +
        "Suggest a clear folder structure and tag scheme. Do NOT rename or move any files — only analyze and recommend."
      )) {
        if (event.type === "chunk") {
          result += event.content;
          setOrganizeResult(result);
        }
      }
      // Refresh document list after analysis
      await fetchDocuments(activeProjectId);
      await fetchTags(activeProjectId);
    } catch (e) {
      console.error("Organize files failed:", e);
    }
    setOrganizing(false);
  };

  const handleOpenPreview = async (doc: ReclawDocument) => {
    setPreviewDoc(doc);
    selectDocument(doc.id);
    setLoadingPreview(true);
    try {
      const content = await documentsApi.content(doc.id);
      setPreviewContent(content);
    } catch {
      setPreviewContent(null);
    }
    setLoadingPreview(false);
  };

  const handleClosePreview = () => {
    setPreviewDoc(null);
    setPreviewContent(null);
    selectDocument(null);
  };

  const handleDelete = async (id: string) => {
    await deleteDocument(id);
    setConfirmDelete(null);
    if (previewDoc?.id === id) handleClosePreview();
  };

  const handleSearchKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Escape") {
        setSearchQuery("");
        (e.target as HTMLInputElement).blur();
      }
    },
    [setSearchQuery]
  );

  // Preview mode
  if (previewDoc) {
    return (
      <DocumentPreview
        doc={previewDoc}
        content={previewContent}
        loading={loadingPreview}
        onClose={handleClosePreview}
      />
    );
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-950">
      <ViewOnboarding viewId="documents" title="Your Research Files" description="All documents in your project — uploaded files, agent outputs, and task results. Drag files here, link an external folder, or use Organize for AI categorization." chatPrompt="How do I organize my documents?" />
      {/* Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileText size={20} className="text-istara-600" />
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Documents</h2>
            {stats && (
              <span className="text-xs bg-slate-200 dark:bg-slate-700 px-2 py-0.5 rounded-full text-slate-500">
                {stats.total}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* View mode toggle */}
            <div className="flex items-center border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden" role="group" aria-label="View mode">
              <button
                onClick={() => handleViewMode("compact")}
                className={cn(
                  "p-1.5 transition-colors",
                  viewMode === "compact"
                    ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                    : "text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600"
                )}
                aria-label="Compact view"
                aria-pressed={viewMode === "compact"}
                title="Compact view"
              >
                <AlignJustify size={14} />
              </button>
              <button
                onClick={() => handleViewMode("grid")}
                className={cn(
                  "p-1.5 transition-colors",
                  viewMode === "grid"
                    ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                    : "text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600"
                )}
                aria-label="Grid view"
                aria-pressed={viewMode === "grid"}
                title="Grid view"
              >
                <LayoutGrid size={14} />
              </button>
              <button
                onClick={() => handleViewMode("list")}
                className={cn(
                  "p-1.5 transition-colors",
                  viewMode === "list"
                    ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                    : "text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600"
                )}
                aria-label="List view"
                aria-pressed={viewMode === "list"}
                title="List view"
              >
                <List size={14} />
              </button>
            </div>

            <button
              onClick={() => setShowFilters(!showFilters)}
              className={cn(
                "flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors",
                showFilters
                  ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              )}
              aria-label="Toggle filters"
              aria-expanded={showFilters}
            >
              <Filter size={14} />
              Filters
            </button>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
              aria-label="Sync project files"
              title="Scan project folder for new files"
            >
              <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
              Sync
            </button>
            <button
              onClick={handleOrganize}
              disabled={organizing}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
              aria-label="Organize files"
              title="AI-powered document organization suggestions"
            >
              <Wand2 size={14} className={organizing ? "animate-pulse" : ""} />
              Organize
            </button>
          </div>
        </div>

        {/* Organize Files Result */}
        {organizeResult && (
          <div className="rounded-lg border border-istara-200 dark:border-istara-800 bg-istara-50 dark:bg-istara-900/20 p-4 max-h-48 overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-istara-700 dark:text-istara-400">Organization Suggestions</span>
              <button onClick={() => setOrganizeResult("")} className="text-slate-400 hover:text-slate-600" aria-label="Close suggestions">
                <X size={14} />
              </button>
            </div>
            <div className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{organizeResult}</div>
          </div>
        )}

        {/* Search bar */}
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search documents by title, content, tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            className="w-full pl-9 pr-8 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-istara-500"
            aria-label="Search documents"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700"
              aria-label="Clear search"
            >
              <X size={12} className="text-slate-400" />
            </button>
          )}
        </div>

        {/* Filters panel */}
        {showFilters && (
          <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Document filters">
            {/* Phase filter */}
            <select
              value={filterPhase}
              onChange={(e) => setFilterPhase(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-istara-500"
              aria-label="Filter by phase"
            >
              {PHASES.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>

            {/* Source filter */}
            <select
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-istara-500"
              aria-label="Filter by source"
            >
              {SOURCES.map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>

            {/* Tag filter */}
            {tags.length > 0 && (
              <select
                value={filterTag}
                onChange={(e) => setFilterTag(e.target.value)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-istara-500"
                aria-label="Filter by tag"
              >
                <option value="">All Tags</option>
                {tags.map((t) => (
                  <option key={t.name} value={t.name}>
                    {t.name} ({t.count})
                  </option>
                ))}
              </select>
            )}

            {/* Clear filters */}
            {(filterPhase || filterSource || filterTag) && (
              <button
                onClick={() => {
                  setFilterPhase("");
                  setFilterSource("");
                  setFilterTag("");
                }}
                className="px-3 py-1.5 rounded-lg text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                aria-label="Clear all filters"
              >
                Clear Filters
              </button>
            )}
          </div>
        )}
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto p-4" role="list" aria-label="Documents list">
        {loading && documents.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={20} className="animate-spin text-istara-600" />
            <span className="ml-2 text-sm text-slate-500">Loading documents...</span>
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12">
            <FileText size={40} className="mx-auto text-slate-300 dark:text-slate-600 mb-3" />
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">
              {searchQuery || filterPhase || filterTag || filterSource
                ? "No documents match your filters."
                : "No documents yet."}
            </p>
            <p className="text-xs text-slate-400">
              Upload files, run skills, or complete tasks to generate documents.
            </p>
          </div>
        ) : (
          <div
            className={cn(
              viewMode === "grid"
                ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3"
                : viewMode === "compact"
                  ? "divide-y divide-slate-100 dark:divide-slate-800"
                  : "space-y-1.5"
            )}
          >
            {documents.map((doc) =>
              viewMode === "compact" ? (
                <DocumentCompactRow
                  key={doc.id}
                  doc={doc}
                  onOpen={() => handleOpenPreview(doc)}
                  onDelete={() => setConfirmDelete(doc.id)}
                  isSelected={selectedDocId === doc.id}
                />
              ) : viewMode === "grid" ? (
                <DocumentGridCard
                  key={doc.id}
                  doc={doc}
                  onOpen={() => handleOpenPreview(doc)}
                  onDelete={() => setConfirmDelete(doc.id)}
                  isSelected={selectedDocId === doc.id}
                />
              ) : (
                <DocumentCard
                  key={doc.id}
                  doc={doc}
                  onOpen={() => handleOpenPreview(doc)}
                  onDelete={() => setConfirmDelete(doc.id)}
                  isSelected={selectedDocId === doc.id}
                />
              )
            )}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-4 pt-4 border-t border-slate-200 dark:border-slate-800">
            <button
              onClick={() => activeProjectId && fetchDocuments(activeProjectId, page - 1)}
              disabled={page <= 1}
              className="px-3 py-1 rounded text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30"
              aria-label="Previous page"
            >
              Previous
            </button>
            <span className="text-xs text-slate-500">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => activeProjectId && fetchDocuments(activeProjectId, page + 1)}
              disabled={page >= totalPages}
              className="px-3 py-1 rounded text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30"
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* Delete confirmation */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl max-w-sm w-full p-5">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-2">Delete Document?</h3>
            <p className="text-sm text-slate-500 mb-4">This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmDelete(null)}
                className="px-3 py-1.5 rounded-lg text-sm text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(confirmDelete)}
                className="px-3 py-1.5 rounded-lg text-sm bg-red-600 text-white hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Document Compact Row ---

function DocumentCompactRow({
  doc,
  onOpen,
  onDelete,
  isSelected,
}: {
  doc: ReclawDocument;
  onOpen: () => void;
  onDelete: () => void;
  isSelected: boolean;
}) {
  const Icon = fileIcon(doc.file_type);

  return (
    <div
      role="listitem"
      className={cn(
        "group flex items-center gap-2 px-3 py-1.5 cursor-pointer transition-colors",
        isSelected
          ? "bg-istara-50 dark:bg-istara-900/10"
          : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
      )}
      onClick={onOpen}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(); } }}
      tabIndex={0}
      aria-label={`Document: ${doc.title}`}
    >
      <Icon size={14} className="text-slate-400 shrink-0" />
      <span className="text-sm text-slate-900 dark:text-white truncate flex-1 font-medium">
        {doc.title}
      </span>
      <span className={cn("text-xs px-1.5 py-0.5 rounded font-medium shrink-0", STATUS_COLORS[doc.status] || STATUS_COLORS.ready)}>
        {doc.status}
      </span>
      <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 shrink-0">
        {SOURCE_LABELS[doc.source] || doc.source}
      </span>
      <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 shrink-0">
        {doc.phase}
      </span>
      <span className="text-xs text-slate-400 shrink-0 whitespace-nowrap">
        {timeAgo(doc.updated_at || doc.created_at)}
      </span>
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        <button
          onClick={(e) => { e.stopPropagation(); onOpen(); }}
          className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400"
          aria-label="Preview document"
          title="Preview"
        >
          <Eye size={13} />
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-slate-400 hover:text-red-600"
          aria-label="Delete document"
          title="Delete"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  );
}

// --- Document Grid Card ---

function DocumentGridCard({
  doc,
  onOpen,
  onDelete,
  isSelected,
}: {
  doc: ReclawDocument;
  onOpen: () => void;
  onDelete: () => void;
  isSelected: boolean;
}) {
  const Icon = fileIcon(doc.file_type);

  return (
    <div
      role="listitem"
      className={cn(
        "group h-[140px] overflow-hidden rounded-lg border transition-all cursor-pointer flex flex-col p-3",
        isSelected
          ? "border-istara-500 bg-istara-50/50 dark:bg-istara-900/10"
          : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-istara-300 hover:shadow-sm dark:hover:border-istara-700"
      )}
      onClick={onOpen}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(); } }}
      tabIndex={0}
      aria-label={`Document: ${doc.title}`}
    >
      {/* Top: icon + title + actions */}
      <div className="flex items-start gap-2 mb-1.5">
        <div className="p-1.5 rounded bg-slate-100 dark:bg-slate-700 shrink-0">
          <Icon size={14} className="text-slate-500 dark:text-slate-400" />
        </div>
        <h4 className="text-sm font-medium text-slate-900 dark:text-white truncate flex-1">
          {doc.title}
        </h4>
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); onOpen(); }}
            className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400"
            aria-label="Preview document"
            title="Preview"
          >
            <Eye size={13} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-slate-400 hover:text-red-600"
            aria-label="Delete document"
            title="Delete"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Description */}
      {doc.description && (
        <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mb-auto">
          {doc.description}
        </p>
      )}
      {!doc.description && <div className="mb-auto" />}

      {/* Bottom metadata row */}
      <div className="flex items-center gap-1.5 mt-1.5 pt-1.5 border-t border-slate-100 dark:border-slate-700">
        <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-medium", STATUS_COLORS[doc.status] || STATUS_COLORS.ready)}>
          {doc.status}
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">
          {doc.phase}
        </span>
        <span className="text-[10px] text-slate-400 ml-auto whitespace-nowrap">
          {timeAgo(doc.updated_at || doc.created_at)}
        </span>
      </div>
    </div>
  );
}

// --- Document Card (List mode) ---

function DocumentCard({
  doc,
  onOpen,
  onDelete,
  isSelected,
}: {
  doc: ReclawDocument;
  onOpen: () => void;
  onDelete: () => void;
  isSelected: boolean;
}) {
  const Icon = fileIcon(doc.file_type);
  const tags = doc.tags || [];

  return (
    <div
      role="listitem"
      className={cn(
        "group p-2 rounded-lg border transition-all cursor-pointer",
        isSelected
          ? "border-istara-500 bg-istara-50/50 dark:bg-istara-900/10"
          : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-istara-300 hover:shadow-sm dark:hover:border-istara-700"
      )}
      onClick={onOpen}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(); } }}
      tabIndex={0}
      aria-label={`Document: ${doc.title}`}
    >
      <div className="flex items-start gap-3">
        {/* File icon */}
        <div className="mt-0.5 p-2 rounded-lg bg-slate-100 dark:bg-slate-700 shrink-0">
          <Icon size={18} className="text-slate-500 dark:text-slate-400" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="text-sm font-medium text-slate-900 dark:text-white truncate">
              {doc.title}
            </h4>
            <span className={cn("text-[10px] px-1.5 py-0.5 rounded-full font-medium", STATUS_COLORS[doc.status] || STATUS_COLORS.ready)}>
              {doc.status}
            </span>
          </div>

          {/* Description */}
          {doc.description && (
            <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-1 mb-1">
              {doc.description}
            </p>
          )}

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-2 text-[10px] text-slate-400">
            {/* Source */}
            <span className="flex items-center gap-0.5">
              <FolderInput size={10} />
              {SOURCE_LABELS[doc.source] || doc.source}
            </span>

            {/* Phase */}
            <span className="flex items-center gap-0.5">
              <Diamond size={10} />
              {doc.phase}
            </span>

            {/* File size */}
            {doc.file_size > 0 && (
              <span>{formatSize(doc.file_size)}</span>
            )}

            {/* Time */}
            <span className="flex items-center gap-0.5">
              <Clock size={10} />
              {timeAgo(doc.updated_at || doc.created_at)}
            </span>

            {/* Agents */}
            {doc.agent_ids.length > 0 && (
              <span className="flex items-center gap-0.5">
                <Bot size={10} />
                {doc.agent_ids.length} agent{doc.agent_ids.length > 1 ? "s" : ""}
              </span>
            )}

            {/* Skills */}
            {doc.skill_names.length > 0 && (
              <span className="flex items-center gap-0.5">
                <Wand2 size={10} />
                {doc.skill_names.length} skill{doc.skill_names.length > 1 ? "s" : ""}
              </span>
            )}

            {/* Task */}
            {doc.task_id && (
              <span className="flex items-center gap-0.5">
                <LayoutDashboard size={10} />
                Task linked
              </span>
            )}
          </div>

          {/* Tags */}
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {tags.slice(0, 5).map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] bg-istara-50 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                >
                  <Tag size={8} />
                  {tag}
                </span>
              ))}
              {tags.length > 5 && (
                <span className="text-[10px] text-slate-400">+{tags.length - 5}</span>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); onOpen(); }}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400"
            aria-label="Preview document"
            title="Preview"
          >
            <Eye size={14} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-slate-400 hover:text-red-600"
            aria-label="Delete document"
            title="Delete"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

// --- Document Preview ---

function DocumentPreview({
  doc,
  content,
  loading,
  onClose,
}: {
  doc: ReclawDocument;
  content: DocumentContent | null;
  loading: boolean;
  onClose: () => void;
}) {
  const atomicPath = doc.atomic_path || {};
  const hasAtomicPath = Object.keys(atomicPath).length > 0;
  const [metaPanelCollapsed, setMetaPanelCollapsed] = useState(false);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 p-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
            aria-label="Back to documents list"
          >
            <ArrowLeft size={18} />
          </button>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white truncate">
              {doc.title}
            </h2>
            <p className="text-xs text-slate-500">
              {doc.file_name} {doc.file_size > 0 && `(${formatSize(doc.file_size)})`}
            </p>
          </div>
          <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", STATUS_COLORS[doc.status])}>
            {doc.status}
          </span>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Main content area */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={20} className="animate-spin text-istara-600" />
              <span className="ml-2 text-sm text-slate-500">Loading content...</span>
            </div>
          ) : content?.content ? (
            <pre className="whitespace-pre-wrap text-sm text-slate-800 dark:text-slate-200 font-mono leading-relaxed bg-slate-50 dark:bg-slate-900 rounded-lg p-4 border border-slate-200 dark:border-slate-700">
              {content.content}
            </pre>
          ) : content?.media_url ? (
            <div className="flex items-center justify-center py-8">
              {content.type && [".jpg", ".jpeg", ".png", ".gif"].includes(content.type) ? (
                <img src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${content.media_url}`} alt={doc.title} className="max-h-96 rounded-lg" />
              ) : content.type && [".mp3", ".wav", ".m4a", ".ogg"].includes(content.type) ? (
                <audio controls src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${content.media_url}`} className="w-full max-w-lg" />
              ) : content.type && [".mp4", ".webm", ".mov"].includes(content.type) ? (
                <video controls src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${content.media_url}`} className="max-h-96 rounded-lg" />
              ) : (
                <p className="text-sm text-slate-500">Preview not available for this file type.</p>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <FileText size={40} className="mx-auto text-slate-300 dark:text-slate-600 mb-3" />
              <p className="text-sm text-slate-500">No preview available.</p>
            </div>
          )}
        </div>

        {/* Right panel collapse toggle */}
        <div className="flex flex-col items-center justify-start py-2 border-l border-slate-200 dark:border-slate-800">
          <button
            onClick={() => setMetaPanelCollapsed(!metaPanelCollapsed)}
            className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
            aria-label={metaPanelCollapsed ? "Expand metadata panel" : "Collapse metadata panel"}
            title={metaPanelCollapsed ? "Expand details" : "Collapse details"}
          >
            {metaPanelCollapsed ? <PanelRight size={16} /> : <PanelRightClose size={16} />}
          </button>
        </div>

        {/* Right panel — metadata */}
        {!metaPanelCollapsed && (
        <div className="w-64 border-l border-slate-200 dark:border-slate-800 overflow-y-auto p-4" role="region" aria-label="Document details">
          {/* Description / Origin */}
          <MetaSection title="Origin">
            <p className="text-xs text-slate-600 dark:text-slate-400">
              {doc.description || "No description available."}
            </p>
          </MetaSection>

          {/* Source & Phase */}
          <MetaSection title="Details">
            <div className="space-y-1.5 text-xs">
              <MetaRow label="Source" value={SOURCE_LABELS[doc.source] || doc.source} />
              <MetaRow label="Phase" value={phaseLabel(doc.phase)} />
              <MetaRow label="Version" value={`v${doc.version}`} />
              <MetaRow label="Created" value={doc.created_at ? new Date(doc.created_at).toLocaleString() : "—"} />
              {doc.updated_at && doc.updated_at !== doc.created_at && (
                <MetaRow label="Updated" value={new Date(doc.updated_at).toLocaleString()} />
              )}
            </div>
          </MetaSection>

          {/* Agents involved */}
          {doc.agent_ids.length > 0 && (
            <MetaSection title="Agents Involved">
              <div className="space-y-1">
                {doc.agent_ids.map((id) => (
                  <div key={id} className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                    <Bot size={12} className="text-istara-600" />
                    <span className="truncate">{id}</span>
                  </div>
                ))}
              </div>
            </MetaSection>
          )}

          {/* Skills involved */}
          {doc.skill_names.length > 0 && (
            <MetaSection title="Skills Used">
              <div className="flex flex-wrap gap-1">
                {doc.skill_names.map((s) => (
                  <span key={s} className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                    <Wand2 size={8} />
                    {s}
                  </span>
                ))}
              </div>
            </MetaSection>
          )}

          {/* Task link */}
          {doc.task_id && (
            <MetaSection title="Related Task">
              <div className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                <LayoutDashboard size={12} className="text-blue-600" />
                <span className="truncate">{doc.task_id}</span>
              </div>
            </MetaSection>
          )}

          {/* Tags */}
          {doc.tags.length > 0 && (
            <MetaSection title="Tags">
              <div className="flex flex-wrap gap-1">
                {doc.tags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] bg-istara-50 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                  >
                    <Tag size={8} />
                    {tag}
                  </span>
                ))}
              </div>
            </MetaSection>
          )}

          {/* Atomic Research Path */}
          {hasAtomicPath && (
            <MetaSection title="Atomic Research Path">
              <div className="space-y-2 text-xs">
                {Object.entries(atomicPath).map(([key, value]) => (
                  <div key={key} className="flex items-start gap-2">
                    <ChevronRight size={10} className="mt-0.5 text-istara-500 shrink-0" />
                    <div>
                      <span className="font-medium text-slate-700 dark:text-slate-300 capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      <p className="text-slate-500 dark:text-slate-400">
                        {typeof value === "string" ? value : JSON.stringify(value)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </MetaSection>
          )}
        </div>
        )}
      </div>
    </div>
  );
}

// --- Helper Sub-components ---

function MetaSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h4 className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">{title}</h4>
      {children}
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-700 dark:text-slate-300 font-medium">{value}</span>
    </div>
  );
}
