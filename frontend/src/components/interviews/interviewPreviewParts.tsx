import { useCallback, useEffect, useRef, useState } from "react";
import NextImage from "next/image";
import {
  ChevronDown,
  Eye,
  FileText,
  Film,
  Image,
  Loader2,
  Plus,
  Send,
  Tag,
  Volume2,
  X,
} from "lucide-react";

import { files as filesApi } from "@/lib/api";
import { API_BASE } from "@/lib/runtimeConfig";
import { useAgentStore } from "@/stores/agentStore";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";

export function fileIcon(type: string) {
  if ([".mp3", ".wav", ".m4a", ".ogg"].includes(type)) return Volume2;
  if ([".mp4", ".webm", ".mov"].includes(type)) return Film;
  if ([".jpg", ".jpeg", ".png", ".gif", ".webp"].includes(type)) return Image;
  return FileText;
}

export function isImage(type: string) {
  return [".jpg", ".jpeg", ".png", ".gif", ".webp"].includes(type);
}

function escapeRegex(str: string) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function TagCreatePopover({
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

export function FilePreview({
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
  const [previewMeta, setPreviewMeta] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const preRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    setLoading(true);
    setContent(null);
    setPreviewMeta(null);
    filesApi
      .content(projectId, filename)
      .then((res: any) => {
        setContent(res.content || null);
        setPreviewMeta(res);
      })
      .catch(() => {
        setContent(null);
        setPreviewMeta(null);
      })
      .finally(() => setLoading(false));
  }, [projectId, filename]);

  useEffect(() => {
    if (!preRef.current) return;
    const mark = preRef.current.querySelector("mark");
    if (mark) {
      mark.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [activeTag, highlightText, content]);

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

  if (isImage(fileType)) {
    return (
      <div className="flex justify-center p-4">
        <NextImage
          src={`${API_BASE}/api/files/${projectId}/serve/${encodeURIComponent(filename)}`}
          alt={filename}
          width={960}
          height={640}
          unoptimized
          className="max-w-full max-h-[60vh] rounded-lg shadow-md"
        />
      </div>
    );
  }

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

        {previewMeta?.document_status === "processing" && !content && (
          <div className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-300">
            <Loader2 size={16} className="animate-spin" />
            Transcription is still processing.
          </div>
        )}

        {previewMeta?.document_status === "error" && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300">
            Transcription failed. Check server dependencies and retry upload.
          </div>
        )}

        {content && (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 px-1">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Transcription</h3>
              {previewMeta?.transcription?.language && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                  {previewMeta.transcription.language}
                </span>
              )}
              {previewMeta?.transcription?.needs_review && (
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                  Review
                </span>
              )}
            </div>
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

  if (!content) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-slate-400 gap-2">
        <Eye size={24} className="text-slate-300" />
        <p className="text-xs">Preview not available for this file type.</p>
      </div>
    );
  }

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

export function SendToAgentButton({
  tags,
  activeTag,
}: {
  tags: string[];
  activeTag: string | null;
}) {
  const { agents, fetchAgents } = useAgentStore();
  const { activeProjectId } = useProjectStore();
  const [open, setOpen] = useState(false);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchAgents(activeProjectId || undefined);
  }, [activeProjectId, fetchAgents]);

  const tagsToSend = activeTag ? [activeTag] : tags;

  const handleSendToAgent = async (agentId: string | null) => {
    setOpen(false);
    setSending(true);
    try {
      const tagList = tagsToSend.join(", ");
      const message = `Investigate these research tags in depth: ${tagList}. Search the project database for evidence related to these themes, identify patterns, and provide a detailed analysis.`;
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
