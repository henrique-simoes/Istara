"use client";

import { useEffect, useState, useRef } from "react";
import {
  Mic,
  Play,
  Pause,
  Tag,
  Sparkles,
  ChevronRight,
  Upload,
  FileText,
  Clock,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { files as filesApi, findings as findingsApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface TranscriptSegment {
  timestamp: string;
  speaker: string;
  text: string;
  nuggetIds: string[];
  highlighted: boolean;
}

export default function InterviewView() {
  const { activeProjectId } = useProjectStore();
  const [projectFiles, setProjectFiles] = useState<any[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [transcriptText, setTranscriptText] = useState("");
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [nuggets, setNuggets] = useState<any[]>([]);
  const [tags, setTags] = useState<Record<string, number>>({});
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [manualHighlight, setManualHighlight] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!activeProjectId) return;
    filesApi.list(activeProjectId).then((r) => setProjectFiles(r.files || [])).catch(() => {});
    findingsApi.nuggets(activeProjectId).then((n) => {
      setNuggets(n);
      // Build tag counts
      const tagCounts: Record<string, number> = {};
      n.forEach((nug: any) => {
        (nug.tags || []).forEach((t: string) => {
          tagCounts[t] = (tagCounts[t] || 0) + 1;
        });
      });
      setTags(tagCounts);
    }).catch(() => {});
  }, [activeProjectId]);

  // Parse transcript into segments when text changes
  useEffect(() => {
    if (!transcriptText) {
      setSegments([]);
      return;
    }
    const parsed = parseTranscript(transcriptText);
    setSegments(parsed);
  }, [transcriptText]);

  const handleFileSelect = async (filename: string) => {
    setSelectedFile(filename);
    // In a real implementation, we'd fetch the file content from the API
    // For now, show a placeholder
    setTranscriptText(
      `[File: ${filename}]\n\nTranscript content would be loaded here.\n\nTo see full transcript analysis, use the chat:\n"Analyze the interview transcript ${filename}"`
    );
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeProjectId) return;
    try {
      await filesApi.upload(activeProjectId, file);
      const r = await filesApi.list(activeProjectId);
      setProjectFiles(r.files || []);
    } catch (err) {
      console.error("Upload failed:", err);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
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
      {/* Left: Transcript */}
      <div className="flex-1 flex flex-col border-r border-slate-200 dark:border-slate-800">
        {/* File selector header */}
        <div className="flex items-center justify-between p-3 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <Mic size={18} className="text-reclaw-600" />
            <h2 className="font-semibold text-slate-900 dark:text-white text-sm">
              🎙️ Interviews & Transcripts
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".txt,.pdf,.docx,.md,.csv"
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

        {/* File list (horizontal tabs) */}
        {projectFiles.length > 0 && (
          <div className="flex gap-1 p-2 overflow-x-auto border-b border-slate-200 dark:border-slate-800">
            {projectFiles.map((f) => (
              <button
                key={f.name}
                onClick={() => handleFileSelect(f.name)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs whitespace-nowrap transition-colors",
                  selectedFile === f.name
                    ? "bg-reclaw-100 dark:bg-reclaw-900/30 text-reclaw-700"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200"
                )}
              >
                <FileText size={12} />
                {f.name}
              </button>
            ))}
          </div>
        )}

        {/* Transcript content */}
        <div className="flex-1 overflow-y-auto p-4">
          {!selectedFile ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3">
              <Mic size={40} className="text-slate-300" />
              <p className="text-sm">Select a file above or upload a transcript</p>
              <p className="text-xs">Supported: TXT, PDF, DOCX, MD</p>
            </div>
          ) : segments.length > 0 ? (
            <div className="space-y-3">
              {segments.map((seg, i) => (
                <div
                  key={i}
                  className={cn(
                    "rounded-lg p-3 transition-colors",
                    seg.highlighted
                      ? "bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400"
                      : "hover:bg-slate-50 dark:hover:bg-slate-800/30"
                  )}
                >
                  <div className="flex items-center gap-2 mb-1">
                    {seg.timestamp && (
                      <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                        <Clock size={10} /> {seg.timestamp}
                      </span>
                    )}
                    {seg.speaker && (
                      <span className="text-xs font-medium text-reclaw-600">{seg.speaker}</span>
                    )}
                  </div>
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                    {seg.text}
                  </p>
                  {seg.nuggetIds.length > 0 && (
                    <div className="flex items-center gap-1 mt-1.5">
                      <Sparkles size={10} className="text-purple-500" />
                      <span className="text-[10px] text-purple-500">
                        {seg.nuggetIds.length} nugget(s) extracted
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <pre className="text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap font-mono leading-relaxed">
              {transcriptText}
            </pre>
          )}
        </div>
      </div>

      {/* Right: Tags & Nuggets */}
      <div className="w-80 flex flex-col bg-slate-50 dark:bg-slate-900">
        {/* Tags */}
        <div className="p-3 border-b border-slate-200 dark:border-slate-800">
          <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1">
            <Tag size={12} /> Tags
          </h3>
          {Object.keys(tags).length === 0 ? (
            <p className="text-xs text-slate-400">No tags yet. Run interview analysis to extract themes.</p>
          ) : (
            <div className="flex flex-wrap gap-1">
              <button
                onClick={() => setActiveTag(null)}
                className={cn(
                  "text-xs px-2 py-0.5 rounded-full transition-colors",
                  !activeTag
                    ? "bg-reclaw-600 text-white"
                    : "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
                )}
              >
                All ({nuggets.length})
              </button>
              {Object.entries(tags)
                .sort((a, b) => b[1] - a[1])
                .map(([tag, count]) => (
                  <button
                    key={tag}
                    onClick={() => setActiveTag(activeTag === tag ? null : tag)}
                    className={cn(
                      "text-xs px-2 py-0.5 rounded-full transition-colors",
                      activeTag === tag
                        ? "bg-purple-600 text-white"
                        : "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400"
                    )}
                  >
                    {tag} ({count})
                  </button>
                ))}
            </div>
          )}
        </div>

        {/* Nuggets extracted */}
        <div className="flex-1 overflow-y-auto p-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase mb-2 flex items-center gap-1">
            <Sparkles size={12} /> Nuggets ({filteredNuggets.length})
          </h3>

          {filteredNuggets.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-8">
              No nuggets extracted yet. Upload transcripts and run "analyze interviews" in chat.
            </p>
          ) : (
            <div className="space-y-2">
              {filteredNuggets.map((nugget) => (
                <div
                  key={nugget.id}
                  className="p-2.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
                >
                  <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                    "{nugget.text}"
                  </p>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <span className="text-[10px] text-slate-400">
                      📄 {(nugget.source || "").split("/").pop()}
                    </span>
                    {nugget.source_location && (
                      <span className="text-[10px] text-slate-400">
                        @ {nugget.source_location}
                      </span>
                    )}
                    {(nugget.tags || []).map((tag: string, i: number) => (
                      <span
                        key={i}
                        className="text-[10px] bg-purple-100 dark:bg-purple-900/30 rounded px-1 py-0.5 text-purple-600"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Linked insights */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800">
          <h3 className="text-xs font-semibold text-slate-500 uppercase mb-1">🔗 Quick Actions</h3>
          <div className="space-y-1">
            <button className="w-full text-left text-xs text-reclaw-600 hover:text-reclaw-700 py-1">
              → Run thematic analysis on all nuggets
            </button>
            <button className="w-full text-left text-xs text-reclaw-600 hover:text-reclaw-700 py-1">
              → Generate affinity map
            </button>
            <button className="w-full text-left text-xs text-reclaw-600 hover:text-reclaw-700 py-1">
              → Create synthesis report
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Helpers ---

function parseTranscript(text: string): TranscriptSegment[] {
  const lines = text.split("\n");
  const segments: TranscriptSegment[] = [];

  // Try to detect timestamp + speaker patterns
  // Patterns: [0:00] Speaker: text, 00:00 - Speaker: text, Speaker (00:00): text
  const patterns = [
    /^\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*([^:]+):\s*(.+)/,
    /^(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–]\s*([^:]+):\s*(.+)/,
    /^([^(]+)\s*\((\d{1,2}:\d{2}(?::\d{2})?)\):\s*(.+)/,
  ];

  let currentSegment: TranscriptSegment | null = null;

  for (const line of lines) {
    if (!line.trim()) {
      if (currentSegment) {
        segments.push(currentSegment);
        currentSegment = null;
      }
      continue;
    }

    let matched = false;
    for (const pattern of patterns) {
      const match = line.match(pattern);
      if (match) {
        if (currentSegment) segments.push(currentSegment);
        // Pattern 3 has speaker first, timestamp second
        const isPattern3 = pattern === patterns[2];
        currentSegment = {
          timestamp: isPattern3 ? match[2] : match[1],
          speaker: (isPattern3 ? match[1] : match[2]).trim(),
          text: match[3].trim(),
          nuggetIds: [],
          highlighted: false,
        };
        matched = true;
        break;
      }
    }

    if (!matched) {
      if (currentSegment) {
        currentSegment.text += " " + line.trim();
      } else {
        currentSegment = {
          timestamp: "",
          speaker: "",
          text: line.trim(),
          nuggetIds: [],
          highlighted: false,
        };
      }
    }
  }

  if (currentSegment) segments.push(currentSegment);
  return segments;
}
