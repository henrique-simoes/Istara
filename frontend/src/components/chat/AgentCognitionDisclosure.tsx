"use client";

import React, { useState } from "react";
import {
  Brain,
  Wrench,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Terminal,
} from "lucide-react";
import type { ToolCallExecution } from "@/lib/types";

interface AgentCognitionDisclosureProps {
  thoughts?: string[];
  toolCalls?: ToolCallExecution[];
  isStreaming?: boolean;
  activeTool?: string | null;
  agentName?: string;
  defaultExpanded?: boolean;
}

export function extractCognitionFromContent(rawContent: string): {
  cleanContent: string;
  thoughts: string[];
  toolCalls: ToolCallExecution[];
} {
  let content = rawContent || "";
  const thoughts: string[] = [];
  const toolCalls: ToolCallExecution[] = [];

  // 1. Extract <think>...</think> blocks
  const thinkRegex = /<think>([\s\S]*?)<\/think>/gi;
  let thinkMatch;
  while ((thinkMatch = thinkRegex.exec(content)) !== null) {
    if (thinkMatch[1].trim()) {
      thoughts.push(thinkMatch[1].trim());
    }
  }
  content = content.replace(thinkRegex, "").trim();

  // 2. Extract legacy tool call formats: **tool_name**: {result}
  const toolResultRegex = /(?:^|\n)\*\*([a-zA-Z0-9_\-\.]+)\*\*:\s*([\s\S]*?)(?=(?:\n\*\*[a-zA-Z0-9_\-\.]+\*\*:|\n\n[A-Z]|$))/g;
  let toolMatch;
  while ((toolMatch = toolResultRegex.exec(content)) !== null) {
    const toolName = toolMatch[1].trim();
    const resultText = toolMatch[2].trim();
    if (
      toolName.includes("_") ||
      toolName.toLowerCase().startsWith("search") ||
      toolName.toLowerCase().startsWith("fetch") ||
      toolName.toLowerCase().startsWith("run") ||
      toolName.toLowerCase().startsWith("query") ||
      toolName.toLowerCase().startsWith("get")
    ) {
      toolCalls.push({
        id: `extracted-${toolCalls.length}`,
        tool: toolName,
        result: resultText,
        status: "completed",
      });
    }
  }

  if (toolCalls.length > 0) {
    content = content.replace(toolResultRegex, "").trim();
  }

  // 3. Extract [Tool: name] badges
  const badgeRegex = /\[Tool:\s*([a-zA-Z0-9_\-\.]+)\]/g;
  let badgeMatch;
  while ((badgeMatch = badgeRegex.exec(content)) !== null) {
    const toolName = badgeMatch[1].trim();
    if (!toolCalls.some((tc) => tc.tool === toolName)) {
      toolCalls.push({
        id: `badge-${toolCalls.length}`,
        tool: toolName,
        status: "completed",
      });
    }
  }
  content = content.replace(badgeRegex, "").trim();

  return { cleanContent: content, thoughts, toolCalls };
}

export default function AgentCognitionDisclosure({
  thoughts = [],
  toolCalls = [],
  isStreaming = false,
  activeTool = null,
  agentName = "Agent",
  defaultExpanded = false,
}: AgentCognitionDisclosureProps) {
  const [isOpen, setIsOpen] = useState(defaultExpanded);
  const [activeTab, setActiveTab] = useState<"all" | "thoughts" | "tools">("all");

  const hasThoughts = thoughts.length > 0;
  const hasTools = toolCalls.length > 0;

  if (!hasThoughts && !hasTools && !isStreaming && !activeTool) {
    return null;
  }

  let summaryLabel = "";
  if (isStreaming) {
    if (activeTool) {
      summaryLabel = `Using tool: ${activeTool}...`;
    } else if (hasTools) {
      const lastTool = toolCalls[toolCalls.length - 1];
      summaryLabel = lastTool.status === "running" ? `Using ${lastTool.tool}...` : "Executing tools...";
    } else {
      summaryLabel = "Thinking...";
    }
  } else {
    if (hasThoughts && hasTools) {
      summaryLabel = `Thought process & ${toolCalls.length} tool${toolCalls.length > 1 ? "s" : ""} used`;
    } else if (hasThoughts) {
      summaryLabel = "Thought process";
    } else if (hasTools) {
      summaryLabel = toolCalls.length === 1 ? `Used ${toolCalls[0].tool}` : `Used ${toolCalls.length} tools`;
    }
  }

  return (
    <div className="mb-3 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-slate-50/70 dark:bg-slate-900/50 backdrop-blur-sm overflow-hidden transition-all shadow-xs">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        className="w-full flex items-center justify-between px-3.5 py-2 text-left hover:bg-slate-100/60 dark:hover:bg-slate-800/60 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-istara-500"
      >
        <div className="flex items-center gap-2 min-w-0">
          {isStreaming ? (
            <div className="relative flex items-center justify-center w-4 h-4">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-istara-400 opacity-75" />
              <Loader2 size={13} className="animate-spin text-istara-600 dark:text-istara-400 relative" />
            </div>
          ) : hasTools ? (
            <Wrench size={13} className="text-slate-500 dark:text-slate-400 shrink-0" />
          ) : (
            <Brain size={13} className="text-purple-500 dark:text-purple-400 shrink-0" />
          )}

          <span
            className={`text-xs font-medium truncate ${
              isStreaming
                ? "text-istara-700 dark:text-istara-300 font-semibold animate-pulse"
                : "text-slate-600 dark:text-slate-400"
            }`}
          >
            {summaryLabel}
          </span>
        </div>

        <div className="flex items-center gap-1.5 shrink-0 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
          <span className="text-[11px] font-normal">{isOpen ? "Hide details" : "Inspect"}</span>
          {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>

      {isOpen && (
        <div className="border-t border-slate-200/60 dark:border-slate-800/60 p-3 text-xs space-y-3 bg-white/40 dark:bg-slate-950/40">
          {hasThoughts && hasTools && (
            <div className="flex items-center gap-1 border-b border-slate-200/60 dark:border-slate-800/60 pb-2 mb-2">
              <button
                type="button"
                onClick={() => setActiveTab("all")}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                  activeTab === "all"
                    ? "bg-slate-200 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                    : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                }`}
              >
                All ({thoughts.length + toolCalls.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("thoughts")}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                  activeTab === "thoughts"
                    ? "bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300"
                    : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                }`}
              >
                Reasoning ({thoughts.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("tools")}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                  activeTab === "tools"
                    ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                    : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                }`}
              >
                Tools ({toolCalls.length})
              </button>
            </div>
          )}

          {(activeTab === "all" || activeTab === "thoughts") && hasThoughts && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-purple-700 dark:text-purple-400">
                <Brain size={12} />
                <span>Internal Reasoning</span>
              </div>
              <div className="pl-3 border-l-2 border-purple-300 dark:border-purple-700 text-slate-600 dark:text-slate-400 whitespace-pre-wrap leading-relaxed font-sans text-xs bg-purple-50/30 dark:bg-purple-950/20 py-1.5 pr-2 rounded-r">
                {thoughts.join("\n\n")}
              </div>
            </div>
          )}

          {(activeTab === "all" || activeTab === "tools") && (hasTools || activeTool) && (
            <div className="space-y-2.5">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                <Terminal size={12} />
                <span>Tool Executions</span>
              </div>

              <div className="space-y-2">
                {toolCalls.map((call, idx) => (
                  <div
                    key={call.id || `tool-${idx}`}
                    className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-2.5 shadow-2xs"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5 font-mono text-[11px] font-medium text-slate-800 dark:text-slate-200">
                        <Wrench size={12} className="text-slate-400" />
                        <span>{call.tool}</span>
                      </div>

                      <div className="flex items-center gap-1">
                        {call.status === "running" ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                            <Loader2 size={10} className="animate-spin" /> Running
                          </span>
                        ) : call.status === "error" ? (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300">
                            <AlertCircle size={10} /> Error
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300">
                            <CheckCircle2 size={10} /> Done
                          </span>
                        )}
                      </div>
                    </div>

                    {call.params && Object.keys(call.params).length > 0 && (
                      <div className="mt-1.5">
                        <div className="text-[10px] font-medium text-slate-400 mb-0.5">Parameters:</div>
                        <pre className="p-1.5 rounded bg-slate-100 dark:bg-slate-950 font-mono text-[10px] text-slate-700 dark:text-slate-300 overflow-x-auto max-h-32">
                          {typeof call.params === "string" ? call.params : JSON.stringify(call.params, null, 2)}
                        </pre>
                      </div>
                    )}

                    {call.result && (
                      <div className="mt-1.5">
                        <div className="text-[10px] font-medium text-slate-400 mb-0.5">Output:</div>
                        <pre className="p-1.5 rounded bg-slate-100 dark:bg-slate-950 font-mono text-[10px] text-slate-700 dark:text-slate-300 overflow-x-auto max-h-40 whitespace-pre-wrap">
                          {call.result}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}

                {isStreaming && activeTool && !toolCalls.some((t) => t.tool === activeTool && t.status === "running") && (
                  <div className="rounded-lg border border-blue-200 dark:border-blue-900 bg-blue-50/40 dark:bg-blue-950/20 p-2 flex items-center justify-between animate-pulse">
                    <div className="flex items-center gap-2 font-mono text-[11px] text-blue-700 dark:text-blue-300">
                      <Loader2 size={12} className="animate-spin" />
                      <span>Calling {activeTool}...</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
