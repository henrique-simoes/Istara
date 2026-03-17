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
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { useAgentStore } from "@/stores/agentStore";
import { files as filesApi, findings as findingsApi, chat as chatApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ApiError } from "@/hooks/useApiCall";

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

/* ── File Content Preview ── */
function FilePreview({
  projectId,
  filename,
  fileType,
  activeTag,
}: {
  projectId: string;
  filename: string;
  fileType: string;
  activeTag: string | null;
}) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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
      <div className="p-4">
        <div className="bg-slate-100 dark:bg-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Volume2 size={16} className="text-reclaw-600" />
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{filename}</span>
          </div>
          <audio
            controls
            className="w-full"
            src={`${API_BASE}/api/files/${projectId}/serve/${encodeURIComponent(filename)}`}
          />
        </div>
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

  // Highlight tag matches in content
  if (activeTag && content) {
    const regex = new RegExp(`(${activeTag.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
    const parts = content.split(regex);
    return (
      <pre className="text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap font-mono leading-relaxed p-4">
        {parts.map((part, i) =>
          regex.test(part) ? (
            <mark key={i} className="bg-purple-200 dark:bg-purple-800/50 text-purple-900 dark:text-purple-200 rounded px-0.5">
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
    <pre className="text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap font-mono leading-relaxed p-4">
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
        new CustomEvent("reclaw:navigate", {
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
        className="flex items-center gap-1 px-3 py-1.5 text-xs bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50"
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
            <span className="text-sm">🐾</span> ReClaw (Main)
          </button>
          {agents
            .filter((a) => a.is_active && a.id !== "reclaw-main")
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
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || !activeProjectId) return;
    setError(null);

    for (const file of Array.from(fileList)) {
      try {
        await filesApi.upload(activeProjectId, file);
      } catch (err: any) {
        setError(`Upload failed: ${err.message}`);
      }
    }
    await loadProjectData();
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFileSelect = (filename: string, type: string) => {
    setSelectedFile(filename);
    setSelectedFileType(type);
    setAnalysisResult("");
  };

  const handleAnalyze = async () => {
    if (!activeProjectId || !selectedFile) return;
    setAnalyzing(true);
    setAnalysisResult("");
    setError(null);

    try {
      let result = "";
      for await (const event of chatApi.send(activeProjectId, `analyze the interview transcript ${selectedFile}`)) {
        if (event.type === "chunk") {
          result += event.content;
          setAnalysisResult(result);
        } else if (event.type === "error") {
          setError(event.message);
        }
      }
      await loadProjectData();
    } catch (e: any) {
      setError(e.message || "Analysis failed");
    }
    setAnalyzing(false);
  };

  const handleBatchAnalyze = async () => {
    if (!activeProjectId || projectFiles.length === 0) return;
    setAnalyzing(true);
    setAnalysisResult("");
    setError(null);

    try {
      let result = "";
      for await (const event of chatApi.send(activeProjectId, `analyze all interview transcripts in this project`)) {
        if (event.type === "chunk") {
          result += event.content;
          setAnalysisResult(result);
        }
      }
      await loadProjectData();
    } catch (e: any) {
      setError(e.message || "Batch analysis failed");
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
      {/* Left: File preview & transcript */}
      <div className="flex-1 flex flex-col border-r border-slate-200 dark:border-slate-800">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-slate-200 dark:border-slate-800">
          <h2 className="font-semibold text-slate-900 dark:text-white text-sm flex items-center gap-2">
            <Mic size={16} className="text-reclaw-600" />
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
              className="flex items-center gap-1 px-3 py-1.5 text-xs bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700"
            >
              <Upload size={12} /> Upload
            </button>
          </div>
        </div>

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
                  setAnalysisResult("");
                  try {
                    let result = "";
                    for await (const event of chatApi.send(activeProjectId, "organize and rename all files in this project by type and category")) {
                      if (event.type === "chunk") { result += event.content; setAnalysisResult(result); }
                    }
                    await loadProjectData();
                  } catch (e) {}
                  setAnalyzing(false);
                }}
                disabled={analyzing}
                className="flex items-center gap-1 px-2 py-1 text-[10px] text-reclaw-600 hover:text-reclaw-700 hover:bg-reclaw-50 dark:hover:bg-reclaw-900/20 rounded-md disabled:opacity-50"
              >
                <Wand2 size={10} /> Organize Files
              </button>
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              {projectFiles.map((f) => {
                const shortName = (() => {
                  const name = f.name || "";
                  const parts = name.split("/");
                  const filename = parts[parts.length - 1];
                  const stripped = filename.replace(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}[-_]/i, "");
                  if (stripped.length <= 24) return stripped;
                  const ext = stripped.lastIndexOf(".") > 0 ? stripped.slice(stripped.lastIndexOf(".")) : "";
                  return stripped.slice(0, 20) + "..." + ext;
                })();
                const Icon = fileIcon(f.type || "");
                return (
                  <button
                    key={f.name}
                    onClick={() => handleFileSelect(f.name, f.type || "")}
                    className={cn(
                      "flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-colors text-left",
                      selectedFile === f.name
                        ? "bg-reclaw-100 dark:bg-reclaw-900/30 text-reclaw-700"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200"
                    )}
                  >
                    <Icon size={12} className="shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="truncate font-medium">{shortName}</p>
                      <p className="text-[10px] text-slate-400">{(f.size_bytes / 1024).toFixed(0)} KB</p>
                    </div>
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
                Upload interview transcripts (TXT, PDF, DOCX), audio recordings, or video files and ReClaw will extract nuggets, themes, and insights.
              </p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-2 px-4 py-2 bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 text-sm mt-2"
              >
                <Upload size={14} /> Upload Files
              </button>
            </div>
          ) : !selectedFile ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2 p-4">
              <ChevronRight size={24} className="text-slate-300" />
              <p className="text-sm">Select a file above to preview</p>
            </div>
          ) : (
            <div>
              {/* Analyze button */}
              {selectedFile && !analyzing && !isMedia(selectedFileType) && !isImage(selectedFileType) && (
                <div className="p-4 pb-0">
                  <button
                    onClick={handleAnalyze}
                    className="flex items-center gap-2 px-4 py-2 bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 text-sm"
                  >
                    <Sparkles size={14} /> Analyze this file
                  </button>
                </div>
              )}

              {/* Analysis result (streaming) */}
              {analysisResult && (
                <div className="mx-4 mt-3 rounded-xl bg-reclaw-50 dark:bg-reclaw-900/10 border border-reclaw-200 dark:border-reclaw-800 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles size={14} className="text-reclaw-600" />
                    <span className="text-xs font-semibold text-reclaw-700 dark:text-reclaw-400">
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
                <FilePreview
                  projectId={activeProjectId}
                  filename={selectedFile}
                  fileType={selectedFileType}
                  activeTag={activeTag}
                />
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right: Tags & Nuggets */}
      <div className="w-80 flex flex-col bg-slate-50 dark:bg-slate-900">
        {/* Tags */}
        <div className="p-3 border-b border-slate-200 dark:border-slate-800">
          <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1">
            <Tag size={12} /> Tags ({Object.keys(tags).length})
          </h3>
          {Object.keys(tags).length === 0 ? (
            <p className="text-xs text-slate-400">Run interview analysis to extract themes and tags.</p>
          ) : (
            <div className="flex flex-wrap gap-1">
              <button
                onClick={() => setActiveTag(null)}
                className={cn(
                  "text-xs px-2 py-0.5 rounded-full transition-colors",
                  !activeTag ? "bg-reclaw-600 text-white" : "bg-slate-200 dark:bg-slate-700 text-slate-600"
                )}
              >
                All ({nuggets.length})
              </button>
              {Object.entries(tags).sort((a, b) => b[1] - a[1]).map(([tag, count]) => (
                <button
                  key={tag}
                  onClick={() => setActiveTag(activeTag === tag ? null : tag)}
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
                No nuggets yet. Upload transcripts and click "Analyze" to extract evidence.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredNuggets.map((nugget) => (
                <div key={nugget.id} className="p-2.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                    &ldquo;{nugget.text}&rdquo;
                  </p>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <span className="text-[10px] text-slate-400">
                      {(nugget.source || "").split("/").pop()}
                    </span>
                    {nugget.source_location && (
                      <span className="text-[10px] text-slate-400">@ {nugget.source_location}</span>
                    )}
                    {(nugget.tags || []).map((tag: string, i: number) => (
                      <button
                        key={i}
                        onClick={() => setActiveTag(activeTag === tag ? null : tag)}
                        className={cn(
                          "text-[10px] rounded px-1 py-0.5 transition-colors",
                          activeTag === tag
                            ? "bg-purple-600 text-white"
                            : "bg-purple-100 dark:bg-purple-900/30 text-purple-600 hover:bg-purple-200"
                        )}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick actions */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800">
          <h3 className="text-xs font-semibold text-slate-500 uppercase mb-1">Quick Actions</h3>
          <div className="space-y-1">
            {[
              { label: "Run thematic analysis on nuggets", intent: "run thematic analysis on all nuggets" },
              { label: "Generate affinity map", intent: "create affinity map from findings" },
              { label: "Create synthesis report", intent: "synthesize all findings into a report" },
            ].map((action) => (
              <button
                key={action.label}
                onClick={async () => {
                  if (!activeProjectId) return;
                  setAnalyzing(true);
                  setAnalysisResult("");
                  try {
                    let result = "";
                    for await (const event of chatApi.send(activeProjectId, action.intent)) {
                      if (event.type === "chunk") { result += event.content; setAnalysisResult(result); }
                    }
                    await loadProjectData();
                  } catch (e) {}
                  setAnalyzing(false);
                }}
                disabled={analyzing}
                className="w-full text-left text-xs text-reclaw-600 hover:text-reclaw-700 py-1 disabled:opacity-50"
              >
                → {action.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
