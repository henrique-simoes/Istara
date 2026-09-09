"use client";

import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import {
  Mic,
  Tag,
  Sparkles,
  Upload,
  FileText,
  Play,
  ChevronRight,
  Loader2,
  X,
  FolderOpen,
  Wand2,
  Highlighter,
  BarChart3,
  PanelRightClose,
  PanelRight,
  ArrowLeft,
  Search,
  Filter,
  Volume2,
  Film,
  Image as ImageIcon,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { files as filesApi, findings as findingsApi, chat as chatApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ApiError } from "@/hooks/useApiCall";
import ViewOnboarding from "@/components/common/ViewOnboarding";
import { FilePreview, SendToAgentButton, TagCreatePopover, fileIcon, isImage } from "./interviewPreviewParts";

function cleanFilename(name: string): string {
  const parts = (name || "").split("/");
  const raw = parts[parts.length - 1] || "";
  return raw.replace(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}[-_]/i, "");
}

/* ── Main InterviewView ── */

export default function InterviewView() {
  const { activeProjectId } = useProjectStore();
  const [projectFiles, setProjectFiles] = useState<any[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedFileType, setSelectedFileType] = useState<string>("");
  const [nuggets, setNuggets] = useState<any[]>([]);
  const [tags, setTags] = useState<Record<string, number>>({});
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [highlightText, setHighlightText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Search and format filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [formatFilter, setFormatFilter] = useState<"all" | "audio" | "transcripts">("all");

  // Right panel collapse state
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false);

  // Tag creation state
  const [tagCreatePopover, setTagCreatePopover] = useState<{
    text: string;
    position: { x: number; y: number };
  } | null>(null);

  const loadProjectData = useCallback(async () => {
    if (!activeProjectId) return;
    setLoading(true);
    setError(null);
    try {
      const [fileResult, nuggetResult] = await Promise.all([
        filesApi.list(activeProjectId),
        findingsApi.nuggets(activeProjectId),
      ]);
      const files = fileResult.files || [];
      setProjectFiles(files);
      setNuggets(nuggetResult);

      // Build tag counts
      const tagCounts: Record<string, number> = {};
      nuggetResult.forEach((nug: any) => {
        (nug.tags || []).forEach((t: string) => {
          tagCounts[t] = (tagCounts[t] || 0) + 1;
        });
      });
      setTags(tagCounts);

      // Default to first file if none selected
      if (files.length > 0 && !selectedFile) {
        setSelectedFile(files[0].name);
        setSelectedFileType(files[0].type || "");
      }
    } catch (e: any) {
      setError(e.message || "Failed to load project data");
    }
    setLoading(false);
  }, [activeProjectId, selectedFile]);

  useEffect(() => {
    loadProjectData();
  }, [loadProjectData]);

  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || !activeProjectId) return;
    setError(null);

    const files = Array.from(fileList);
    setUploading(true);
    setUploadProgress({ current: 0, total: files.length });

    let successCount = 0;
    let failCount = 0;
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        await filesApi.upload(activeProjectId, file);
        successCount++;
      } catch (err: any) {
        failCount++;
        setError(`Upload failed for ${file.name}: ${err.message}`);
      }
      setUploadProgress({ current: i + 1, total: files.length });
    }

    await loadProjectData();
    setUploading(false);
    setUploadProgress({ current: 0, total: 0 });
    if (fileInputRef.current) fileInputRef.current.value = "";

    if (successCount > 0) {
      dispatchToast("success", "Files Uploaded", `${successCount} file(s) uploaded successfully`);
    }
    if (failCount > 0) {
      dispatchToast("warning", "Upload Errors", `${failCount} file(s) failed to upload`);
    }
  };

  const handleFileSelect = (filename: string, type: string) => {
    setSelectedFile(filename);
    setSelectedFileType(type);
    setAnalysisResult("");
    setHighlightText(null);
  };

  // Click a nugget → navigate to its source file and highlight the nugget text
  const handleNuggetClick = (nugget: any) => {
    const source = nugget.source || "";
    const matchFile = projectFiles.find(
      (f) => source.includes(f.name) || f.name.includes(source.split("/").pop() || "")
    );
    if (matchFile) {
      setSelectedFile(matchFile.name);
      setSelectedFileType(matchFile.type || "");
    }
    setHighlightText(nugget.text.slice(0, 100));
  };

  // Handle tag click
  const handleTagClick = (tag: string | null) => {
    const newTag = activeTag === tag ? null : tag;
    setActiveTag(newTag);
    setHighlightText(null);

    if (newTag) {
      const tagNuggets = nuggets.filter((n) => (n.tags || []).includes(newTag));
      if (tagNuggets.length > 0) {
        const currentFileHasTag =
          selectedFile &&
          tagNuggets.some((n) => (n.source || "").includes((selectedFile || "").split("/").pop() || "___"));
        if (!currentFileHasTag) {
          for (const nugget of tagNuggets) {
            const source = nugget.source || "";
            const matchFile = projectFiles.find(
              (f) => source.includes(f.name) || f.name.includes(source.split("/").pop() || "___")
            );
            if (matchFile) {
              setSelectedFile(matchFile.name);
              setSelectedFileType(matchFile.type || "");
              break;
            }
          }
        }
      }
    }
  };

  // Tag creation from text selection in file preview
  const handleTextSelect = (text: string, position: { x: number; y: number }) => {
    setTagCreatePopover({ text, position });
  };

  const handleCreateTag = async (tagName: string) => {
    if (!activeProjectId || !tagCreatePopover) return;
    setTagCreatePopover(null);

    try {
      await findingsApi.createNugget(activeProjectId, {
        text: tagCreatePopover.text,
        source: selectedFile || "manual",
        source_location: "",
        tags: [tagName],
      });
      await loadProjectData();
      dispatchToast("success", "Tag Created", `\"${tagName}\" added to ${selectedFile || "selection"}`);
    } catch (_e: any) {
      setTags((prev) => ({ ...prev, [tagName]: (prev[tagName] || 0) + 1 }));
      dispatchToast("warning", "Tag Saved Locally", "Could not sync with server. Tag will be lost on refresh.");
    }
  };

  const dispatchToast = (type: "success" | "warning" | "info", title: string, message: string) => {
    window.dispatchEvent(new CustomEvent("istara:toast", { detail: { type, title, message } }));
  };

  const handleChatStream = async (
    projectId: string,
    message: string,
    onChunk: (text: string) => void,
    onComplete?: (toolsUsed: string[]) => void,
  ): Promise<{ error: string | null }> => {
    let result = "";
    const toolsUsed: string[] = [];
    try {
      for await (const event of chatApi.send(projectId, message)) {
        if (event.type === "chunk") {
          result += event.content;
          onChunk(result);
        } else if (event.type === "tool_call") {
          toolsUsed.push(event.tool || "unknown");
          onChunk(result + `\n\n▸ Running: ${event.tool}...`);
        } else if (event.type === "error") {
          return { error: event.message };
        }
      }
      onComplete?.(toolsUsed);
      return { error: null };
    } catch (e: any) {
      return { error: e.message || "Request failed" };
    }
  };

  const handleAnalyze = async () => {
    if (!activeProjectId || !selectedFile) return;
    setAnalyzing(true);
    setAnalysisResult("Starting interview analysis...");
    setError(null);

    const { error } = await handleChatStream(
      activeProjectId,
      `analyze the interview transcript ${selectedFile}`,
      (text) => setAnalysisResult(text),
      (tools) => {
        dispatchToast("success", "Analysis Complete", `Analyzed ${selectedFile} using ${tools.length} tool(s)`);
      },
    );

    if (error) {
      setError(error);
      dispatchToast("warning", "Analysis Failed", error);
    } else {
      await loadProjectData();
    }
    setAnalyzing(false);
  };

  const handleBatchAnalyze = async () => {
    if (!activeProjectId || projectFiles.length === 0) return;
    setAnalyzing(true);
    setAnalysisResult("Starting batch analysis of all transcripts...");
    setError(null);

    const { error } = await handleChatStream(
      activeProjectId,
      `analyze all interview transcripts in this project`,
      (text) => setAnalysisResult(text),
      (tools) => {
        dispatchToast("success", "Batch Analysis Complete", `Analyzed ${projectFiles.length} file(s) using ${tools.length} tool(s)`);
      },
    );

    if (error) {
      setError(error);
      dispatchToast("warning", "Batch Analysis Failed", error);
    } else {
      await loadProjectData();
    }
    setAnalyzing(false);
  };

  // Filtered files for the master sidebar
  const filteredFiles = useMemo(() => {
    return projectFiles.filter((f) => {
      const type = (f.type || "").toLowerCase();
      const isAudio = [".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".webm", ".mov"].includes(type);
      if (formatFilter === "audio" && !isAudio) return false;
      if (formatFilter === "transcripts" && isAudio) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const clean = cleanFilename(f.display_name || f.name).toLowerCase();
        const matchName = clean.includes(q) || (f.name || "").toLowerCase().includes(q);
        const fileNuggets = nuggets.filter((n) => (n.source || "").includes(f.name.split("/").pop() || ""));
        const matchTag = fileNuggets.some((n) => (n.tags || []).some((t: string) => t.toLowerCase().includes(q)));
        return matchName || matchTag;
      }
      return true;
    });
  }, [projectFiles, formatFilter, searchQuery, nuggets]);

  // Active file nuggets
  const activeFileNuggets = useMemo(() => {
    if (!selectedFile) return [];
    const baseName = selectedFile.split("/").pop() || "";
    return nuggets.filter((n) => (n.source || "").includes(baseName));
  }, [nuggets, selectedFile]);

  const filteredNuggets = activeTag
    ? nuggets.filter((n) => (n.tags || []).includes(activeTag))
    : nuggets;

  const currentFileObj = projectFiles.find((f) => f.name === selectedFile);

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <p>Select a project to view interviews.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden bg-white dark:bg-slate-950">
      <ViewOnboarding
        viewId="interviews"
        title="Interview Analysis Workbench"
        description="Manage interview recordings and transcripts with master-detail navigation, phrase highlights, and grounded qualitative coding."
        chatPrompt="How do I analyze interviews and extract grounded quotes?"
      />

      {/* Tag creation popover */}
      {tagCreatePopover && (
        <TagCreatePopover
          selectedText={tagCreatePopover.text}
          position={tagCreatePopover.position}
          onCreateTag={handleCreateTag}
          onClose={() => setTagCreatePopover(null)}
        />
      )}

      {/* ── 1. Left Column: Master Interview Explorer Sidebar ── */}
      <aside
        className="w-80 border-r border-slate-200 dark:border-slate-800 flex flex-col bg-slate-50/50 dark:bg-slate-900/60 shrink-0"
        aria-label="Interviews explorer"
      >
        {/* Sidebar Header */}
        <div className="p-3 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="flex items-center justify-between gap-2 mb-2.5">
            <h2 className="font-semibold text-slate-900 dark:text-white text-sm flex items-center gap-2">
              <Mic size={16} className="text-istara-600 dark:text-istara-400" />
              Interviews
              <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs text-slate-600 dark:text-slate-300 font-medium">
                {projectFiles.length}
              </span>
            </h2>
            <div className="flex items-center gap-1.5">
              <button
                onClick={async () => {
                  if (!activeProjectId) return;
                  setAnalyzing(true);
                  setAnalysisResult("Organizing files...");
                  const { error } = await handleChatStream(
                    activeProjectId,
                    "organize and rename all files in this project by type and category",
                    (text) => setAnalysisResult(text),
                    () => dispatchToast("success", "Files Organized", "File organization complete"),
                  );
                  if (error) {
                    setError(error);
                    dispatchToast("warning", "Organize Failed", error);
                  } else {
                    await loadProjectData();
                  }
                  setAnalyzing(false);
                }}
                disabled={analyzing}
                title="Organize files with AI"
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
              >
                <Wand2 size={14} />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                accept=".txt,.pdf,.docx,.md,.csv,.mp3,.wav,.m4a,.ogg,.mp4,.webm,.mov,.jpg,.jpeg,.png,.gif"
                onChange={handleFileUpload}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                title="Upload interview audio, video, or transcripts"
                className="flex items-center gap-1 px-2.5 py-1 text-xs bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-70 font-medium shadow-sm transition-colors"
              >
                {uploading ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />}
                <span>Upload</span>
              </button>
            </div>
          </div>

          {/* Search Bar */}
          <div className="relative mb-2">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search by name or tag..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-7 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-istara-500 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <X size={12} />
              </button>
            )}
          </div>

          {/* Format Filter Tabs */}
          <div className="flex items-center gap-1">
            {(
              [
                { id: "all", label: `All (${projectFiles.length})` },
                { id: "audio", label: "Audio/Media" },
                { id: "transcripts", label: "Transcripts" },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setFormatFilter(tab.id)}
                className={cn(
                  "px-2 py-1 text-[11px] rounded-md font-medium transition-colors",
                  formatFilter === tab.id
                    ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                    : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Interview Cards List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {loading && projectFiles.length === 0 ? (
            <div className="flex items-center justify-center py-10 text-slate-400 text-xs gap-2">
              <Loader2 size={16} className="animate-spin" /> Loading interviews...
            </div>
          ) : filteredFiles.length === 0 ? (
            <div className="text-center py-10 px-4 text-slate-400">
              <Mic size={32} className="mx-auto text-slate-300 dark:text-slate-700 mb-2" />
              <p className="text-xs font-medium text-slate-600 dark:text-slate-400">
                {searchQuery ? "No matching interviews" : "No interview files yet"}
              </p>
              <p className="text-[11px] mt-1 text-slate-400">
                {searchQuery ? "Try searching a different keyword or tag" : "Upload audio, video, or transcripts to start"}
              </p>
            </div>
          ) : (
            filteredFiles.map((f) => {
              const isSelected = selectedFile === f.name;
              const Icon = fileIcon(f.type || "");
              const clean = cleanFilename(f.display_name || f.name);
              const fileNuggets = nuggets.filter((n) =>
                (n.source || "").includes(f.name.split("/").pop() || "")
              );
              const fileTagCounts: Record<string, number> = {};
              fileNuggets.forEach((nug: any) => {
                (nug.tags || []).forEach((t: string) => {
                  fileTagCounts[t] = (fileTagCounts[t] || 0) + 1;
                });
              });
              const topTags = Object.entries(fileTagCounts).sort((a, b) => b[1] - a[1]).slice(0, 3);
              const isAudio = [".mp3", ".wav", ".m4a", ".ogg"].includes(f.type || "");
              const isVideo = [".mp4", ".webm", ".mov"].includes(f.type || "");

              return (
                <div
                  key={f.name}
                  onClick={() => handleFileSelect(f.name, f.type || "")}
                  className={cn(
                    "group relative flex flex-col p-3 rounded-xl border transition-all cursor-pointer text-left",
                    isSelected
                      ? "border-istara-500 bg-istara-50/70 dark:bg-istara-950/40 shadow-sm"
                      : "border-slate-200/80 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900"
                  )}
                >
                  {/* Left accent bar for selected state */}
                  {isSelected && (
                    <div className="absolute left-0 top-2.5 bottom-2.5 w-1 bg-istara-600 rounded-r" />
                  )}

                  {/* Header row with icon and filename */}
                  <div className="flex items-start gap-2.5 min-w-0">
                    <div
                      className={cn(
                        "p-2 rounded-lg shrink-0 mt-0.5",
                        isAudio
                          ? "bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300"
                          : isVideo
                          ? "bg-sky-100 text-sky-700 dark:bg-sky-950/60 dark:text-sky-300"
                          : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                      )}
                    >
                      <Icon size={14} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h4
                        className={cn(
                          "text-xs font-semibold leading-snug truncate",
                          isSelected ? "text-istara-950 dark:text-istara-100" : "text-slate-800 dark:text-slate-200"
                        )}
                        title={clean}
                      >
                        {clean}
                      </h4>
                      <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                        <span className="uppercase font-mono text-[10px] font-medium px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800">
                          {(f.type || "doc").replace(".", "")}
                        </span>
                        <span>{(f.size_bytes / 1024).toFixed(0)} KB</span>
                        {f.document_status === "processing" ? (
                          <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400 font-medium">
                            <Loader2 size={10} className="animate-spin" /> Transcribing
                          </span>
                        ) : fileNuggets.length > 0 ? (
                          <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                            {fileNuggets.length} quotes
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>

                  {/* Tags badge preview on the card */}
                  {topTags.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1 mt-2.5 pt-2 border-t border-slate-100 dark:border-slate-800/60">
                      {topTags.map(([tName, tCount]) => (
                        <span
                          key={tName}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTagClick(tName);
                          }}
                          className={cn(
                            "text-[10px] px-1.5 py-0.5 rounded-full font-medium flex items-center gap-1 transition-colors",
                            activeTag === tName
                              ? "bg-purple-600 text-white"
                              : "bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-200/60 dark:border-purple-800/40 hover:bg-purple-100"
                          )}
                        >
                          <span>#{tName}</span>
                          <span className="opacity-70 text-[9px]">({tCount})</span>
                        </span>
                      ))}
                      {Object.keys(fileTagCounts).length > 3 && (
                        <span className="text-[10px] text-slate-400 ml-0.5">
                          +{Object.keys(fileTagCounts).length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* ── 2. Center Column: Transcript & Media Detail Workbench ── */}
      <main className="flex-1 flex flex-col min-w-0 bg-white dark:bg-slate-950 overflow-hidden">
        {/* Workspace Toolbar Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="min-w-0 flex items-center gap-2">
            {selectedFile ? (
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-semibold text-sm text-slate-900 dark:text-white truncate">
                  {cleanFilename(currentFileObj?.display_name || selectedFile)}
                </span>
                <span className="uppercase font-mono text-[10px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 shrink-0">
                  {(selectedFileType || "doc").replace(".", "")}
                </span>
                {activeFileNuggets.length > 0 && (
                  <span className="text-xs text-slate-500 dark:text-slate-400 hidden sm:inline">
                    • {activeFileNuggets.length} grounded quote(s)
                  </span>
                )}
              </div>
            ) : (
              <span className="text-sm text-slate-500 font-medium">Select an interview to inspect</span>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {selectedFile && !isImage(selectedFileType) && (
              <button
                onClick={handleAnalyze}
                disabled={analyzing}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-70 font-medium shadow-sm transition-colors"
              >
                {analyzing ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                <span>{analyzing ? "Analyzing..." : "Analyze Interview"}</span>
              </button>
            )}

            {projectFiles.length > 1 && (
              <button
                onClick={handleBatchAnalyze}
                disabled={analyzing}
                className="flex items-center gap-1 px-2.5 py-1.5 text-xs bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg transition-colors disabled:opacity-50 font-medium"
              >
                <Play size={12} />
                <span>Batch All</span>
              </button>
            )}

            {Object.keys(tags).length > 0 && activeProjectId && (
              <SendToAgentButton tags={Object.keys(tags)} activeTag={activeTag} />
            )}
          </div>
        </div>

        {/* Tag & Quote Highlight Notification Bar */}
        {(activeTag || highlightText) && (
          <div className="flex items-center justify-between gap-2 px-4 py-2 bg-purple-50/90 dark:bg-purple-950/40 border-b border-purple-200 dark:border-purple-800/60 transition-all">
            <div className="flex items-center gap-2 min-w-0 text-xs text-purple-900 dark:text-purple-200">
              <Highlighter size={14} className="text-purple-600 shrink-0" />
              <span className="truncate font-medium">
                Highlighting: {activeTag && <span className="font-bold">#{activeTag}</span>}
                {activeTag && highlightText && " + "}
                {highlightText && <span className="italic">&ldquo;{highlightText.slice(0, 50)}...&rdquo;</span>}
              </span>
            </div>
            <button
              onClick={() => {
                setActiveTag(null);
                setHighlightText(null);
              }}
              className="flex items-center gap-1 text-[11px] text-purple-700 hover:text-purple-900 dark:text-purple-300 font-medium shrink-0 ml-2"
              title="Clear active highlights"
            >
              <X size={12} /> Clear Filter
            </button>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="p-3">
            <ApiError error={error} onRetry={loadProjectData} />
          </div>
        )}

        {/* Main Transcript Canvas */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-64 text-slate-400 gap-2">
              <Loader2 size={20} className="animate-spin" /> Loading transcript...
            </div>
          ) : !selectedFile ? (
            <div className="flex flex-col items-center justify-center h-64 text-slate-400 gap-3">
              <Mic size={40} className="text-slate-300 dark:text-slate-700" />
              <p className="text-sm font-medium">Select an interview from the list to view transcript and highlights</p>
            </div>
          ) : (
            <div className="space-y-4 max-w-5xl mx-auto">
              {/* Analysis result banner */}
              {analysisResult && (
                <div className="rounded-xl bg-istara-50 dark:bg-istara-950/30 border border-istara-200 dark:border-istara-800 p-4 shadow-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles size={14} className="text-istara-600 dark:text-istara-400" />
                    <span className="text-xs font-semibold text-istara-800 dark:text-istara-300">
                      Qualitative Synthesis {analyzing && "(streaming...)"}
                    </span>
                  </div>
                  <div className={cn("text-xs leading-relaxed text-slate-700 dark:text-slate-300 whitespace-pre-wrap", analyzing && "streaming-cursor")}>
                    {analysisResult}
                  </div>
                </div>
              )}

              {/* File Preview */}
              {activeProjectId && (
                <div className="relative rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden p-4">
                  <FilePreview
                    projectId={activeProjectId}
                    filename={selectedFile}
                    fileType={selectedFileType}
                    activeTag={activeTag}
                    highlightText={highlightText}
                    onTextSelect={handleTextSelect}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* ── 3. Right Column: Inspector Toggle & Panel ── */}
      <div className="flex flex-col items-center justify-start py-2 border-l border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 shrink-0">
        <button
          onClick={() => setRightPanelCollapsed(!rightPanelCollapsed)}
          className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
          aria-label={rightPanelCollapsed ? "Expand tags and nuggets panel" : "Collapse tags and nuggets panel"}
          title={rightPanelCollapsed ? "Expand panel" : "Collapse panel"}
        >
          {rightPanelCollapsed ? <PanelRight size={16} /> : <PanelRightClose size={16} />}
        </button>
      </div>

      {!rightPanelCollapsed && (
        <aside
          className="w-72 flex flex-col bg-slate-50/70 dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shrink-0"
          aria-label="Tags and grounded nuggets"
        >
          {/* Tags Header */}
          <div className="p-3 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase mb-2 flex items-center justify-between">
              <span className="flex items-center gap-1.5"><Tag size={13} className="text-purple-600" /> Tags ({Object.keys(tags).length})</span>
              {activeTag && (
                <button onClick={() => handleTagClick(null)} className="text-[10px] text-purple-600 hover:underline capitalize">
                  Show all
                </button>
              )}
            </h3>

            {Object.keys(tags).length === 0 ? (
              <p className="text-xs text-slate-400">Run interview analysis or select text in transcript to create tags.</p>
            ) : (
              <div className="flex flex-wrap gap-1 max-h-36 overflow-y-auto pt-1">
                <button
                  onClick={() => handleTagClick(null)}
                  className={cn(
                    "text-xs px-2 py-0.5 rounded-full transition-colors font-medium",
                    !activeTag
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                      : "bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-300"
                  )}
                >
                  All ({nuggets.length})
                </button>
                {Object.entries(tags)
                  .sort((a, b) => b[1] - a[1])
                  .map(([tag, count]) => (
                    <button
                      key={tag}
                      onClick={() => handleTagClick(tag)}
                      className={cn(
                        "text-xs px-2 py-0.5 rounded-full transition-colors font-medium flex items-center gap-1",
                        activeTag === tag
                          ? "bg-purple-600 text-white shadow-sm"
                          : "bg-purple-100 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 hover:bg-purple-200"
                      )}
                    >
                      <span>#{tag}</span>
                      <span className="opacity-75 text-[10px]">({count})</span>
                    </button>
                  ))}
              </div>
            )}
          </div>

          {/* Nuggets / Grounded Quotes */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase flex items-center gap-1.5">
                <Sparkles size={13} className="text-amber-500" /> Grounded Quotes ({filteredNuggets.length})
              </h3>
            </div>

            {filteredNuggets.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                <Sparkles size={24} className="mx-auto text-slate-300 dark:text-slate-700 mb-2" />
                <p className="text-xs font-medium">No quotes yet</p>
                <p className="text-[11px] mt-1">Run analysis or highlight transcript text to save quotes.</p>
              </div>
            ) : (
              filteredNuggets.map((nugget) => (
                <div
                  key={nugget.id}
                  onClick={() => handleNuggetClick(nugget)}
                  className={cn(
                    "w-full text-left p-2.5 rounded-xl border transition-all cursor-pointer shadow-xs",
                    highlightText && nugget.text.slice(0, 100) === highlightText
                      ? "bg-amber-50 dark:bg-amber-950/30 border-amber-300 dark:border-amber-700"
                      : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700/80 hover:border-istara-400 dark:hover:border-istara-600"
                  )}
                >
                  <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-serif italic">
                    &ldquo;{nugget.text}&rdquo;
                  </p>
                  <div className="flex items-center gap-2 mt-2 flex-wrap text-[10px] text-slate-500">
                    <span className="font-medium truncate max-w-[130px] flex items-center gap-1">
                      <FileText size={10} />
                      {cleanFilename(nugget.source || "")}
                    </span>
                    {(nugget.tags || []).map((tag: string, i: number) => (
                      <span
                        key={i}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTagClick(tag);
                        }}
                        className={cn(
                          "px-1.5 py-0.2 rounded-full font-medium transition-colors",
                          activeTag === tag
                            ? "bg-purple-600 text-white"
                            : "bg-purple-100 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300"
                        )}
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Quick Qualitative Actions */}
          <div className="p-3 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
            <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Analysis Routines</h4>
            <div className="space-y-1">
              {[
                { label: "Thematic Analysis", intent: "run thematic analysis on all nuggets", icon: Sparkles, toastTitle: "Thematic Analysis Complete" },
                { label: "Affinity Mapping", intent: "create affinity map from findings", icon: FolderOpen, toastTitle: "Affinity Map Generated" },
                { label: "Intercoder Reliability (Kappa)", intent: "run intercoder reliability kappa analysis on all coded data", icon: BarChart3, toastTitle: "Kappa Analysis Complete" },
                { label: "Synthesis Report", intent: "synthesize all findings into a report", icon: FileText, toastTitle: "Synthesis Report Created" },
              ].map((action) => (
                <button
                  key={action.label}
                  onClick={async () => {
                    if (!activeProjectId) return;
                    setAnalyzing(true);
                    setAnalysisResult(`Starting: ${action.label}...`);
                    const { error } = await handleChatStream(
                      activeProjectId,
                      action.intent,
                      (text) => setAnalysisResult(text),
                      () => dispatchToast("success", action.toastTitle, "Analysis complete"),
                    );
                    if (error) {
                      setError(error);
                      dispatchToast("warning", `${action.label} Failed`, error);
                    } else {
                      await loadProjectData();
                    }
                    setAnalyzing(false);
                  }}
                  disabled={analyzing}
                  className="w-full text-left text-xs text-istara-600 dark:text-istara-400 hover:text-istara-700 dark:hover:text-istara-300 py-1.5 px-2 rounded-md hover:bg-istara-50 dark:hover:bg-istara-950/30 transition-colors disabled:opacity-50 flex items-center gap-2 font-medium"
                >
                  <action.icon size={12} /> {action.label}
                </button>
              ))}
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
