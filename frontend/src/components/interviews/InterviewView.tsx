"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  Mic,
  Tag,
  Sparkles,
  Upload,
  FileText,
  Clock,
  Play,
  ChevronRight,
  Loader2,
  X,
  FolderOpen,
  Wand2,
  Image,
  Film,
  Volume2,
  Bot,
  ChevronDown,
  Send,
  Eye,
  Plus,
  Highlighter,
  BarChart3,
  PanelRightClose,
  PanelRight,
  ArrowLeft,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { useAgentStore } from "@/stores/agentStore";
import { files as filesApi, findings as findingsApi, chat as chatApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ApiError } from "@/hooks/useApiCall";
import ViewOnboarding from "@/components/common/ViewOnboarding";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TranscriptSegment {
  timestamp: string;
  speaker: string;
  text: string;
  highlighted: boolean;
}

/* ── File type helpers ── */
function fileIcon(type: string) {
  if ([".mp3", ".wav", ".m4a", ".ogg"].includes(type)) return Volume2;
  if ([".mp4", ".webm", ".mov"].includes(type)) return Film;
  if ([".jpg", ".jpeg", ".png", ".gif", ".webp"].includes(type)) return Image;
  return FileText;
}

function isMedia(type: string) {
  return [".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".webm", ".mov"].includes(type);
}

function isImage(type: string) {
  return [".jpg", ".jpeg", ".png", ".gif", ".webp"].includes(type);
}

/* ── Escape regex special chars ── */
function escapeRegex(str: string) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/* ── Tag creation popover ── */
function TagCreatePopover({
  selectedText,
  position,
  onCreateTag,
  onClose,
}: {
  selectedText: string;
  position: { x: number; y: number };
  onCreateTag: (tagName: string) => void;
  onClose: () => void;
}) {
  const [tagName, setTagName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = () => {
    const name = tagName.trim() || selectedText.slice(0, 30).trim();
    if (name) onCreateTag(name);
  };

  return (
    <div
      className="fixed z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl p-3 w-64"
      style={{ left: Math.min(position.x, window.innerWidth - 280), top: position.y + 10 }}
    >
      <div className="flex items-center gap-2 mb-2">
        <Tag size={12} className="text-purple-600" />
        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Create Tag</span>
        <button onClick={onClose} className="ml-auto text-slate-400 hover:text-slate-600">
          <X size={12} />
        </button>
      </div>
      <p className="text-[10px] text-slate-400 mb-2 truncate">
        Selected: &ldquo;{selectedText.slice(0, 60)}{selectedText.length > 60 ? "..." : ""}&rdquo;
      </p>
      <input
        ref={inputRef}
        value={tagName}
        onChange={(e) => setTagName(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        placeholder={selectedText.slice(0, 30)}
        className="w-full px-2 py-1.5 text-xs border border-slate-200 dark:border-slate-700 rounded-md bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-1 focus:ring-purple-500 mb-2"
      />
      <button
        onClick={handleSubmit}
        className="w-full px-2 py-1.5 text-xs bg-purple-600 text-white rounded-md hover:bg-purple-700 flex items-center justify-center gap-1"
      >
        <Plus size={10} /> Create Tag
      </button>
    </div>
  );
}

/* ── File Content Preview ── */
function FilePreview({
  projectId,
  filename,
  fileType,
  activeTag,
  highlightText,
  onTextSelect,
}: {
  projectId: string;
  filename: string;
  fileType: string;
  activeTag: string | null;
  highlightText: string | null;
  onTextSelect?: (text: string, position: { x: number; y: number }) => void;
}) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const preRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    setLoading(true);
    setContent(null);
    filesApi
      .content(projectId, filename)
      .then((res: any) => {
        setContent(res.content);
      })
      .catch(() => setContent(null))
      .finally(() => setLoading(false));
  }, [projectId, filename]);

  // Auto-scroll to first highlight match
  useEffect(() => {
    if (!preRef.current) return;
    const mark = preRef.current.querySelector("mark");
    if (mark) {
      mark.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [activeTag, highlightText, content]);

  // Handle text selection for tag creation
  const handleMouseUp = useCallback(() => {
    if (!onTextSelect) return;
    const selection = window.getSelection();
    const text = selection?.toString().trim();
    if (text && text.length > 2) {
      const range = selection?.getRangeAt(0);
      const rect = range?.getBoundingClientRect();
      if (rect) {
        onTextSelect(text, { x: rect.left, y: rect.bottom });
      }
    }
  }, [onTextSelect]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-400">
        <Loader2 size={20} className="animate-spin mr-2" /> Loading preview...
      </div>
    );
  }

  // Image files
  if (isImage(fileType)) {
    return (
      <div className="flex justify-center p-4">
        <img
          src={`${API_BASE}/api/files/${projectId}/serve/${encodeURIComponent(filename)}`}
          alt={filename}
          className="max-w-full max-h-[60vh] rounded-lg shadow-md"
        />
      </div>
    );
  }

  // Audio files
  if ([".mp3", ".wav", ".m4a", ".ogg"].includes(fileType)) {
    return (
      <div className="p-4 space-y-4">
        <div className="bg-slate-100 dark:bg-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Volume2 size={16} className="text-istara-600" />
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{filename}</span>
          </div>
          <audio
            controls
            className="w-full"
            src={`${API_BASE}/api/files/${projectId}/serve/${encodeURIComponent(filename)}`}
          />
        </div>
        
        {content && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-1">Transcription</h3>
            <pre
              ref={preRef}
              onMouseUp={handleMouseUp}
              className="text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap font-mono leading-relaxed p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 select-text cursor-text"
            >
              {content}
            </pre>
          </div>
        )}
      </div>
    );
  }

  // Video files
  if ([".mp4", ".webm", ".mov"].includes(fileType)) {
    return (
      <div className="p-4">
        <video
          controls
          className="w-full max-h-[60vh] rounded-lg"
          src={`${API_BASE}/api/files/${projectId}/serve/${encodeURIComponent(filename)}`}
        />
      </div>
    );
  }

  // Text-based files (txt, md, csv, pdf, docx)
  if (!content) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-slate-400 gap-2">
        <Eye size={24} className="text-slate-300" />
        <p className="text-xs">Preview not available for this file type.</p>
      </div>
    );
  }

  // Build combined highlight patterns (tag + nugget text)
  const patterns: string[] = [];
  if (activeTag) patterns.push(escapeRegex(activeTag));
  if (highlightText) patterns.push(escapeRegex(highlightText));

  if (patterns.length > 0) {
    const regex = new RegExp(`(${patterns.join("|")})`, "gi");
    const parts = content.split(regex);
    return (
      <pre
        ref={preRef}
        onMouseUp={handleMouseUp}
        className="text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap font-mono leading-relaxed p-4 select-text cursor-text"
      >
        {parts.map((part, i) =>
          regex.test(part) ? (
            <mark
              key={i}
              className={cn(
                "rounded px-0.5",
                highlightText && part.toLowerCase() === highlightText.toLowerCase()
                  ? "bg-amber-200 dark:bg-amber-800/50 text-amber-900 dark:text-amber-200"
                  : "bg-purple-200 dark:bg-purple-800/50 text-purple-900 dark:text-purple-200"
              )}
            >
              {part}
            </mark>
          ) : (
            <span key={i}>{part}</span>
          )
        )}
      </pre>
    );
  }

  return (
    <pre
      ref={preRef}
      onMouseUp={handleMouseUp}
      className="text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap font-mono leading-relaxed p-4 select-text cursor-text"
    >
      {content}
    </pre>
  );
}

/* ── Send Tags to Agent Dropdown ── */
function SendToAgentButton({
  projectId,
  tags,
  activeTag,
}: {
  projectId: string;
  tags: string[];
  activeTag: string | null;
}) {
  const { agents, fetchAgents } = useAgentStore();
  const [open, setOpen] = useState(false);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const tagsToSend = activeTag ? [activeTag] : tags;

  const handleSendToAgent = async (agentId: string | null) => {
    setOpen(false);
    setSending(true);
    try {
      const tagList = tagsToSend.join(", ");
      const message = `Investigate these research tags in depth: ${tagList}. Search the project database for evidence related to these themes, identify patterns, and provide a detailed analysis.`;
      // Navigate to chat with the agent
      window.dispatchEvent(
        new CustomEvent("istara:navigate", {
          detail: { view: "chat", agent_id: agentId, prefill: message },
        })
      );
    } catch {}
    setSending(false);
  };

  if (tagsToSend.length === 0) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={sending}
        className="flex items-center gap-1 px-3 py-1.5 text-xs bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50"
      >
        {sending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
        Send to Agent
        <ChevronDown size={10} />
      </button>
      {open && (
        <div className="absolute top-full right-0 mt-1 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg py-1 min-w-[200px]">
          <div className="px-3 py-1.5 text-[10px] text-slate-400 uppercase font-semibold border-b border-slate-100 dark:border-slate-700">
            Choose Agent
          </div>
          <button
            onClick={() => handleSendToAgent(null)}
            className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"
          >
            <span className="text-sm">🐾</span> Istara (Main)
          </button>
          {agents
            .filter((a) => a.is_active && a.id !== "istara-main")
            .map((agent) => (
              <button
                key={agent.id}
                onClick={() => handleSendToAgent(agent.id)}
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"
              >
                <div
                  className="w-4 h-4 rounded-full flex items-center justify-center text-white text-[8px] font-bold"
                  style={{ backgroundColor: `hsl(${agent.name.length * 37 % 360}, 60%, 45%)` }}
                >
                  {agent.name.charAt(0)}
                </div>
                {agent.name}
              </button>
            ))}
        </div>
      )}
    </div>
  );
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
      setProjectFiles(fileResult.files || []);
      setNuggets(nuggetResult);

      // Build tag counts
      const tagCounts: Record<string, number> = {};
      nuggetResult.forEach((nug: any) => {
        (nug.tags || []).forEach((t: string) => {
          tagCounts[t] = (tagCounts[t] || 0) + 1;
        });
      });
      setTags(tagCounts);
    } catch (e: any) {
      setError(e.message || "Failed to load project data");
    }
    setLoading(false);
  }, [activeProjectId]);

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
    // Try to find the file that matches the nugget source
    const matchFile = projectFiles.find(
      (f) => source.includes(f.name) || f.name.includes(source.split("/").pop() || "")
    );
    if (matchFile) {
      setSelectedFile(matchFile.name);
      setSelectedFileType(matchFile.type || "");
    }
    // Highlight the nugget text in the preview
    setHighlightText(nugget.text.slice(0, 100)); // Use first 100 chars to match
  };

  // Handle tag click — navigate to the first file that contains this tag
  const handleTagClick = (tag: string | null) => {
    const newTag = activeTag === tag ? null : tag;
    setActiveTag(newTag);
    setHighlightText(null);

    // If a tag is activated, check if the currently selected file has nuggets with that tag.
    // If not, jump to the first file that does.
    if (newTag) {
      const tagNuggets = nuggets.filter((n) => (n.tags || []).includes(newTag));
      if (tagNuggets.length > 0) {
        const currentFileHasTag = selectedFile && tagNuggets.some(
          (n) => (n.source || "").includes((selectedFile || "").split("/").pop() || "___")
        );
        if (!currentFileHasTag) {
          // Find the first file that has this tag
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

    // Create a nugget with this tag from the selected text
    try {
      await findingsApi.createNugget(activeProjectId, {
        text: tagCreatePopover.text,
        source: selectedFile || "manual",
        source_location: "",
        tags: [tagName],
      });
      await loadProjectData();
      dispatchToast("success", "Tag Created", `"${tagName}" added to ${selectedFile || "selection"}`);
    } catch (e: any) {
      // Fallback: add the tag locally for UX
      setTags((prev) => ({ ...prev, [tagName]: (prev[tagName] || 0) + 1 }));
      dispatchToast("warning", "Tag Saved Locally", "Could not sync with server. Tag will be lost on refresh.");
    }
  };

  /** Dispatch a toast notification — WCAG 2.2 4.1.3 Status Messages, Nielsen H1: Visibility */
  const dispatchToast = (type: "success" | "warning" | "info", title: string, message: string) => {
    window.dispatchEvent(new CustomEvent("istara:toast", { detail: { type, title, message } }));
  };

  /** Handle SSE stream from chat API with full event processing */
  const handleChatStream = async (
    projectId: string,
    message: string,
    onChunk: (text: string) => void,
    onComplete?: (toolsUsed: string[]) => void,
  ): Promise<{ error: string | null }> => {
    let result = "";
    let toolsUsed: string[] = [];
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
    setAnalysisResult("Starting analysis...");
    setError(null);

    const { error } = await handleChatStream(
      activeProjectId,
      `analyze the interview transcript ${selectedFile}`,
      (text) => setAnalysisResult(text),
      (tools) => {
        dispatchToast("success", "Analysis Complete", `Used ${tools.length} tool(s) to analyze ${selectedFile}`);
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

  const filteredNuggets = activeTag
    ? nuggets.filter((n) => (n.tags || []).includes(activeTag))
    : nuggets;

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <p>Select a project to view interviews.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      <ViewOnboarding viewId="interviews" title="Interview Analysis" description="Upload interview transcripts and audio. Agents extract themes, sentiment, key quotes, and participant insights." chatPrompt="How do I analyze interviews?" />
      {/* Tag creation popover */}
      {tagCreatePopover && (
        <TagCreatePopover
          selectedText={tagCreatePopover.text}
          position={tagCreatePopover.position}
          onCreateTag={handleCreateTag}
          onClose={() => setTagCreatePopover(null)}
        />
      )}

      {/* Left: File preview & transcript */}
      <div className="flex-1 flex flex-col border-r border-slate-200 dark:border-slate-800">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-slate-200 dark:border-slate-800">
          <h2 className="font-semibold text-slate-900 dark:text-white text-sm flex items-center gap-2">
            <Mic size={16} className="text-istara-600" />
            Interviews & Transcripts
          </h2>
          <div className="flex items-center gap-2">
            {Object.keys(tags).length > 0 && activeProjectId && (
              <SendToAgentButton
                projectId={activeProjectId}
                tags={Object.keys(tags)}
                activeTag={activeTag}
              />
            )}
            {projectFiles.length > 0 && (
              <button
                onClick={handleBatchAnalyze}
                disabled={analyzing}
                className="flex items-center gap-1 px-3 py-1.5 text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded-lg hover:bg-amber-200 disabled:opacity-50"
              >
                {analyzing ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                Analyze All
              </button>
            )}
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
              className="flex items-center gap-1 px-3 py-1.5 text-xs bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-70"
              aria-busy={uploading}
            >
              {uploading ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />}
              {uploading ? `Uploading ${uploadProgress.current}/${uploadProgress.total}` : "Upload"}
            </button>
          </div>
        </div>

        {/* Tag highlight bar */}
        {(activeTag || highlightText) && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 dark:bg-purple-900/20 border-b border-purple-200 dark:border-purple-800">
            <Highlighter size={12} className="text-purple-600" />
            <span className="text-[11px] text-purple-700 dark:text-purple-300">
              Highlighting: {activeTag && <span className="font-medium">{activeTag}</span>}
              {activeTag && highlightText && " + "}
              {highlightText && <span className="font-medium italic">&ldquo;{highlightText.slice(0, 40)}...&rdquo;</span>}
            </span>
            <button
              onClick={() => { setActiveTag(null); setHighlightText(null); }}
              className="ml-auto text-purple-400 hover:text-purple-600"
            >
              <X size={12} />
            </button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-3">
            <ApiError error={error} onRetry={loadProjectData} />
          </div>
        )}

        {/* File tabs */}
        {projectFiles.length > 0 && (
          <div className="p-3 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-slate-500 uppercase flex items-center gap-1.5">
                <FolderOpen size={12} />
                Files ({projectFiles.length})
              </h3>
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
                className="flex items-center gap-1 px-2 py-1 text-[10px] text-istara-600 hover:text-istara-700 hover:bg-istara-50 dark:hover:bg-istara-900/20 rounded-md disabled:opacity-50"
              >
                <Wand2 size={10} /> Organize Files
              </button>
            </div>
            <div className="flex flex-wrap gap-1">
              {projectFiles.map((f) => {
                const shortName = (() => {
                  const name = f.name || "";
                  const parts = name.split("/");
                  const filename = parts[parts.length - 1];
                  const stripped = filename.replace(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}[-_]/i, "");
                  if (stripped.length <= 20) return stripped;
                  const ext = stripped.lastIndexOf(".") > 0 ? stripped.slice(stripped.lastIndexOf(".")) : "";
                  return stripped.slice(0, 16) + "..." + ext;
                })();
                const Icon = fileIcon(f.type || "");
                // Show indicator if this file has matching nuggets for the active tag
                const hasTagNuggets = activeTag && nuggets.some(
                  (n) => (n.tags || []).includes(activeTag) && (n.source || "").includes(f.name.split("/").pop() || "")
                );
                return (
                  <button
                    key={f.name}
                    onClick={() => handleFileSelect(f.name, f.type || "")}
                    title={`${f.name} (${(f.size_bytes / 1024).toFixed(0)} KB)`}
                    className={cn(
                      "flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] transition-colors text-left",
                      selectedFile === f.name
                        ? "bg-istara-100 dark:bg-istara-900/30 text-istara-700"
                        : hasTagNuggets
                        ? "bg-purple-50 dark:bg-purple-900/20 text-purple-700 border border-purple-200 dark:border-purple-800"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200"
                    )}
                  >
                    <Icon size={11} className="shrink-0" />
                    <span className="truncate font-medium max-w-[120px]">{shortName}</span>
                    {hasTagNuggets && (
                      <div className="w-1.5 h-1.5 rounded-full bg-purple-500 shrink-0" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Content area */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full text-slate-400">
              <Loader2 size={20} className="animate-spin mr-2" /> Loading...
            </div>
          ) : !selectedFile && projectFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3 p-4">
              <Mic size={48} className="text-slate-300" />
              <p className="text-sm font-medium">No interview files yet</p>
              <p className="text-xs text-center max-w-xs">
                Upload interview transcripts (TXT, PDF, DOCX), audio recordings, or video files and Istara will extract nuggets, themes, and insights.
              </p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-2 px-4 py-2 bg-istara-600 text-white rounded-lg hover:bg-istara-700 text-sm mt-2"
              >
                <Upload size={14} /> Upload Files
              </button>
            </div>
          ) : !selectedFile ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2 p-4">
              <ChevronRight size={24} className="text-slate-300" />
              <p className="text-sm">Select a file above to preview</p>
              <p className="text-[10px] text-slate-300 mt-1">Tip: Select text in the preview to create tags</p>
            </div>
          ) : (
            <div>
              {/* Analyze button — Nielsen H1: Visibility, WCAG 2.2 4.1.3 Status Messages */}
              {selectedFile && !isImage(selectedFileType) && (
                <div className="p-4 pb-0">
                  <button
                    onClick={handleAnalyze}
                    disabled={analyzing}
                    className="flex items-center gap-2 px-4 py-2 bg-istara-600 text-white rounded-lg hover:bg-istara-700 text-sm disabled:opacity-70"
                    aria-busy={analyzing}
                  >
                    {analyzing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                    {analyzing ? "Analyzing..." : "Analyze this file"}
                  </button>
                </div>
              )}

              {/* Analysis result (streaming) */}
              {analysisResult && (
                <div className="mx-4 mt-3 rounded-xl bg-istara-50 dark:bg-istara-900/10 border border-istara-200 dark:border-istara-800 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles size={14} className="text-istara-600" />
                    <span className="text-xs font-semibold text-istara-700 dark:text-istara-400">
                      Analysis Result {analyzing && "(streaming...)"}
                    </span>
                  </div>
                  <div className={cn("text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap", analyzing && "streaming-cursor")}>
                    {analysisResult}
                  </div>
                </div>
              )}

              {/* File preview */}
              {activeProjectId && (
                <div className="relative">
                  {/* Back button — WCAG 2.2 2.4.3 Focus Order, Nielsen H8: Back/Close */}
                  <button
                    onClick={() => { setSelectedFile(null); setSelectedFileType(""); }}
                    className="absolute top-2 left-2 z-10 p-2 rounded-lg bg-white/90 dark:bg-slate-800/90 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 shadow-sm border border-slate-200 dark:border-slate-700 transition-colors"
                    aria-label="Back to file list"
                    title="Back to file list"
                  >
                    <ArrowLeft size={18} />
                  </button>
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
      </div>

      {/* Right panel collapse toggle */}
      <div className="flex flex-col items-center justify-start py-2 border-l border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900">
        <button
          onClick={() => setRightPanelCollapsed(!rightPanelCollapsed)}
          className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
          aria-label={rightPanelCollapsed ? "Expand tags and nuggets panel" : "Collapse tags and nuggets panel"}
          title={rightPanelCollapsed ? "Expand panel" : "Collapse panel"}
        >
          {rightPanelCollapsed ? <PanelRight size={16} /> : <PanelRightClose size={16} />}
        </button>
      </div>

      {/* Right: Tags & Nuggets */}
      {!rightPanelCollapsed && (
      <div className="w-64 flex flex-col bg-slate-50 dark:bg-slate-900">
        {/* Tags */}
        <div className="p-3 border-b border-slate-200 dark:border-slate-800">
          <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1">
            <Tag size={12} /> Tags ({Object.keys(tags).length})
          </h3>
          {Object.keys(tags).length === 0 ? (
            <p className="text-xs text-slate-400">Run interview analysis to extract themes and tags, or select text and create tags manually.</p>
          ) : (
            <div className="flex flex-wrap gap-1">
              <button
                onClick={() => handleTagClick(null)}
                className={cn(
                  "text-xs px-2 py-0.5 rounded-full transition-colors",
                  !activeTag ? "bg-istara-600 text-white" : "bg-slate-200 dark:bg-slate-700 text-slate-600"
                )}
              >
                All ({nuggets.length})
              </button>
              {Object.entries(tags).sort((a, b) => b[1] - a[1]).map(([tag, count]) => (
                <button
                  key={tag}
                  onClick={() => handleTagClick(tag)}
                  className={cn(
                    "text-xs px-2 py-0.5 rounded-full transition-colors",
                    activeTag === tag ? "bg-purple-600 text-white" : "bg-purple-100 dark:bg-purple-900/30 text-purple-700"
                  )}
                >
                  {tag} ({count})
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Nuggets */}
        <div className="flex-1 overflow-y-auto p-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1">
            <Sparkles size={12} /> Nuggets ({filteredNuggets.length})
          </h3>

          {filteredNuggets.length === 0 ? (
            <div className="text-center py-8">
              <Sparkles size={24} className="mx-auto text-slate-300 mb-2" />
              <p className="text-xs text-slate-400">
                No nuggets yet. Upload transcripts and click &ldquo;Analyze&rdquo; to extract evidence.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredNuggets.map((nugget) => (
                <button
                  key={nugget.id}
                  onClick={() => handleNuggetClick(nugget)}
                  className={cn(
                    "w-full text-left p-2.5 rounded-lg border transition-colors",
                    highlightText && nugget.text.slice(0, 100) === highlightText
                      ? "bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700"
                      : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-istara-300 dark:hover:border-istara-700"
                  )}
                >
                  <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                    &ldquo;{nugget.text}&rdquo;
                  </p>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                      <FileText size={8} />
                      {(nugget.source || "").split("/").pop()}
                    </span>
                    {nugget.source_location && (
                      <span className="text-[10px] text-slate-400">@ {nugget.source_location}</span>
                    )}
                    {(nugget.tags || []).map((tag: string, i: number) => (
                      <span
                        key={i}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTagClick(tag);
                        }}
                        className={cn(
                          "text-[10px] rounded px-1 py-0.5 transition-colors cursor-pointer",
                          activeTag === tag
                            ? "bg-purple-600 text-white"
                            : "bg-purple-100 dark:bg-purple-900/30 text-purple-600 hover:bg-purple-200"
                        )}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Quick actions */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800">
          <h3 className="text-xs font-semibold text-slate-500 uppercase mb-1">Quick Actions</h3>
          <div className="space-y-1">
            {[
              { label: "Run thematic analysis on nuggets", intent: "run thematic analysis on all nuggets", icon: Sparkles, toastTitle: "Thematic Analysis Complete" },
              { label: "Generate affinity map", intent: "create affinity map from findings", icon: FolderOpen, toastTitle: "Affinity Map Generated" },
              { label: "Intercoder reliability (Kappa)", intent: "run intercoder reliability kappa analysis on all coded data", icon: BarChart3, toastTitle: "Kappa Analysis Complete" },
              { label: "Create synthesis report", intent: "synthesize all findings into a report", icon: FileText, toastTitle: "Synthesis Report Created" },
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
                className="w-full text-left text-xs text-istara-600 hover:text-istara-700 py-1 disabled:opacity-50 flex items-center gap-1.5"
              >
                <action.icon size={10} /> {action.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      )}
    </div>
  );
}
