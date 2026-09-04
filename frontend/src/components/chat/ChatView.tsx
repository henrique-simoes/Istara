"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Paperclip, Loader2, StopCircle, Upload, X, FolderOpen, FileText, Mic, Activity } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChatStore } from "@/stores/chatStore";
import { useProjectStore } from "@/stores/projectStore";
import { useSessionStore } from "@/stores/sessionStore";
import { useAgentStore } from "@/stores/agentStore";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import { useRoleCapabilities } from "@/hooks/useRoleCapabilities";
import { cn, formatDate } from "@/lib/utils";
import { chat as chatApi, files as filesApi, documents as documentsApi, steering as steeringApi } from "@/lib/api";
import ViewOnboarding from "@/components/common/ViewOnboarding";
import ChatSessionsSidebar from "./ChatSessionsSidebar";
import ChatModelControls from "./ChatModelControls";
import type { PiCatalogProvider, PiEndpointInfo } from "@/lib/types";
import { isChatSendReady } from "@/lib/modelCatalog";
import { AgentAvatar, UserAvatar } from "./chatViewParts";

function SteeringQueueIndicator({
  agentId,
  projectId,
  enabled,
}: {
  agentId: string | null;
  projectId: string | null;
  enabled: boolean;
}) {
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    if (!enabled || !agentId || !projectId) {
      setStatus(null);
      return;
    }
    const fetchStatus = async () => {
      try {
        const res = await steeringApi.getAllStatus(projectId);
        setStatus(res[agentId]);
      } catch {}
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [enabled, agentId, projectId]);

  if (!status || (!status.steering_queue_count && !status.follow_up_queue_count)) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800 rounded-lg text-[10px] text-purple-700 dark:text-purple-400 font-medium animate-pulse mb-2">
      <Activity size={10} />
      <span>
        {status.steering_queue_count > 0 && `${status.steering_queue_count} steering message(s) pending`}
        {status.steering_queue_count > 0 && status.follow_up_queue_count > 0 && " • "}
        {status.follow_up_queue_count > 0 && `${status.follow_up_queue_count} follow-up(s) queued`}
      </span>
    </div>
  );
}

export default function ChatView() {
  const { messages, streaming, streamingContent, error, usage, sendMessage, fetchHistory, cancelStreaming, setEngine } = useChatStore();
  const { activeProjectId, canWriteActiveProject } = useProjectStore();
  const { activeSessionId, ensureDefault, updateSession, pendingPrefill, setPendingPrefill, fetchSessions } = useSessionStore();
  const { agents, fetchAgents } = useAgentStore();
  const capabilities = useRoleCapabilities();
  const activeSession = useSessionStore((s) => s.activeSession());
  const { isRecording, isTranscribing, startRecording, stopRecording, cancelRecording, error: voiceError } = useVoiceRecorder();
  const [input, setInput] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [showDocPicker, setShowDocPicker] = useState(false);
  const [pickerDocs, setPickerDocs] = useState<{ id: string; title: string }[]>([]);
  const [pickerSearch, setPickerSearch] = useState("");
  const [pickerLoading, setPickerLoading] = useState(false);
  const [pendingDocRefs, setPendingDocRefs] = useState<{ id: string; title: string }[]>([]);
  const [modelProviders, setModelProviders] = useState<PiCatalogProvider[]>([]);
  const [configuredModels, setConfiguredModels] = useState<PiEndpointInfo[]>([]);
  const [legacyModels, setLegacyModels] = useState<string[]>([]);
  const [modelEngine, setModelEngine] = useState<"pi" | "legacy">("legacy");
  const [chatReady, setChatReady] = useState<boolean | null>(null);
  const [defaultEndpointId, setDefaultEndpointId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const canWrite = capabilities.canWriteActiveProject || canWriteActiveProject();
  const chatUnavailable = !isChatSendReady(modelEngine, chatReady);

  // Initialize sessions: fetch list first (restores localStorage session), then ensure a default exists
  useEffect(() => {
    if (activeProjectId) {
      fetchSessions(activeProjectId).then(() => ensureDefault(activeProjectId));
      fetchAgents(activeProjectId);
      chatApi.modelCatalog(activeProjectId).then((catalog) => {
        setModelProviders(catalog.providers || []);
        setConfiguredModels(catalog.configured || []);
        setLegacyModels(catalog.legacy_models || []);
        setModelEngine(catalog.engine === "pi" ? "pi" : "legacy");
        setChatReady(catalog.chat_ready ?? null);
        setDefaultEndpointId(catalog.default_endpoint_id || null);
        // Keep the request header in lockstep with the visible core chip so
        // what the user sees is exactly what routes the turn (CF-SPEC-1).
        setEngine(catalog.engine === "pi" ? "pi" : "legacy");
      }).catch(() => {
        setModelProviders([]);
        setConfiguredModels([]);
        setLegacyModels([]);
        setModelEngine("legacy");
        setChatReady(false);
        setDefaultEndpointId(null);
        // Catalog unknown: clear the override so the request carries no
        // engine header and the backend uses the persisted choice (F-B1).
        setEngine(null);
      });
    }
  }, [activeProjectId, fetchSessions, ensureDefault, fetchAgents, setEngine]);

  useEffect(() => {
    if (activeProjectId) {
      setLoadingHistory(true);
      fetchHistory(activeProjectId, activeSessionId || undefined).finally(() => setLoadingHistory(false));
    }
  }, [activeProjectId, activeSessionId, fetchHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Auto-send pending prefill message (from "Send to Agent" flow)
  useEffect(() => {
    if (pendingPrefill && activeProjectId && activeSessionId && canWrite && !chatUnavailable && !streaming && !loadingHistory) {
      const msg = pendingPrefill;
      setPendingPrefill(null);
      sendMessage(activeProjectId, msg, activeSessionId);
    }
  }, [pendingPrefill, activeProjectId, activeSessionId, canWrite, chatUnavailable, streaming, loadingHistory, setPendingPrefill, sendMessage]);

  const handleSend = async () => {
    const text = input.trim();
    const files = [...pendingFiles];
    const docRefs = [...pendingDocRefs];
    if (!canWrite || chatUnavailable || (!text && files.length === 0 && docRefs.length === 0) || !activeProjectId || streaming) return;

    setInput("");
    setPendingFiles([]);
    setPendingDocRefs([]);

    // Upload pending files first, collect names
    const uploadedNames: string[] = [];
    for (const file of files) {
      try {
        const result = await filesApi.upload(activeProjectId, file);
        uploadedNames.push(`${file.name} (${result.chunks_indexed} chunks indexed)`);
      } catch (err) {
        console.error("Upload failed:", err);
        uploadedNames.push(`${file.name} (upload failed)`);
      }
    }

    // Build message with attachment context
    let message = text;
    if (uploadedNames.length > 0) {
      const fileList = uploadedNames.join(", ");
      message = text
        ? `${text}\n\n[Attached files: ${fileList}]`
        : `I uploaded: ${fileList}. Please analyze.`;
    }
    if (docRefs.length > 0) {
      const refList = docRefs.map((d) => d.title).join(", ");
      message = message
        ? `${message}\n\n[Referenced project documents: ${refList}]`
        : `Please analyze these project documents: ${refList}`;
    }

    sendMessage(activeProjectId, message, activeSessionId || undefined);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!canWrite) return;
    const files = e.target.files;
    if (!files) return;
    setPendingFiles((prev) => [...prev, ...Array.from(files)]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  /** Dispatch a toast notification — WCAG 2.2 4.1.3 Status Messages */
  const dispatchToast = (type: "success" | "warning" | "info" | "agent" | "file", title: string, message: string) => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("istara:toast", { detail: { type, title, message } }));
    }
  };

  const removePendingFile = (index: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const removePendingDocRef = (id: string) => {
    setPendingDocRefs((prev) => prev.filter((d) => d.id !== id));
  };

  // Document picker
  const openDocPicker = async () => {
    if (!activeProjectId) return;
    setShowDocPicker(true);
    setPickerLoading(true);
    try {
      const data = await documentsApi.list({ project_id: activeProjectId, page_size: 50 });
      setPickerDocs(data.documents || []);
    } catch {
      setPickerDocs([]);
    }
    setPickerLoading(false);
  };

  const searchDocs = async (query: string) => {
    setPickerSearch(query);
    if (!activeProjectId) return;
    if (!query.trim()) {
      openDocPicker();
      return;
    }
    setPickerLoading(true);
    try {
      const data = await documentsApi.list({ project_id: activeProjectId, search: query.trim(), page_size: 30 });
      setPickerDocs(data.documents || []);
    } catch {
      setPickerDocs([]);
    }
    setPickerLoading(false);
  };

  const selectDocRef = (doc: { id: string; title: string }) => {
    if (!pendingDocRefs.find((d) => d.id === doc.id)) {
      setPendingDocRefs((prev) => [...prev, doc]);
    }
    setShowDocPicker(false);
    setPickerSearch("");
  };

  const handleVoiceToggle = async () => {
    if (!canWrite || !activeProjectId) return;
    if (isRecording) {
      const transcribedText = await stopRecording(activeProjectId);
      if (transcribedText) {
        setInput((prev) => (prev ? `${prev} ${transcribedText}` : transcribedText));
      }
    } else {
      await startRecording();
    }
  };

  useEffect(() => {
    if (voiceError) {
      dispatchToast("warning", "Voice Error", voiceError);
    }
  }, [voiceError]);

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <div className="text-center">
          <span className="text-4xl block mb-4">🐾</span>
          <p className="text-lg">Select or create a project to start</p>
        </div>
      </div>
    );
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (!activeProjectId || !canWrite) return;
    const file = e.dataTransfer.files[0];
    if (!file) return;
    try {
      const result = await filesApi.upload(activeProjectId, file);
      await sendMessage(activeProjectId, `I just uploaded "${file.name}" (${result.chunks_indexed} chunks indexed). Can you analyze it?`, activeSessionId || undefined);
    } catch (err) {
      console.error("Drop upload failed:", err);
    }
  };

  return (
    <div className="flex-1 min-w-0 flex min-h-0 overflow-hidden">
      {activeProjectId && (
        <ChatSessionsSidebar projectId={activeProjectId} />
      )}

      {/* Main chat area */}
      <div
        data-chat-workbench="true"
        className={cn("flex-1 min-w-0 flex flex-col min-h-0 overflow-hidden", dragOver && "ring-2 ring-istara-500 ring-inset bg-istara-50/50 dark:bg-istara-900/10")}
        onDragOver={(e) => { e.preventDefault(); if (canWrite) setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <ViewOnboarding viewId="chat" title="Your Research Assistant" description="Chat with your AI agent about research. Upload files, ask questions, or run analysis skills. Agents understand your project context." chatPrompt="What can I do in Chat?" />

        {/* Toolbar */}
        <ChatModelControls
          activeSession={activeSession}
          agents={agents}
          providers={modelProviders}
          configured={configuredModels}
          legacyModels={legacyModels}
          engine={modelEngine}
          defaultEndpointId={defaultEndpointId}
          usage={usage}
          onUpdateSession={(data) => {
            if (activeProjectId && activeSessionId) void updateSession(activeProjectId, activeSessionId, data);
          }}
        />

        {/* Drag overlay */}
        {dragOver && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-istara-50/80 dark:bg-istara-900/80 pointer-events-none">
            <div className="text-center">
              <Upload size={40} className="mx-auto text-istara-500 mb-2" />
              <p className="text-istara-700 dark:text-istara-400 font-medium">Drop files to upload</p>
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="h-0 flex-1 overflow-y-auto p-4 space-y-4" tabIndex={0} role="log" aria-label="Chat messages">
          {messages.length === 0 && !streaming && (
            <div className="flex items-center justify-center h-full text-slate-400">
              <div className="text-center max-w-md">
                <span className="text-4xl block mb-4">🐾</span>
                <p className="text-lg mb-2">Ready to research!</p>
                <p className="text-sm">
                  Upload interview transcripts, ask research questions, or drop files to get started.
                </p>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "message-enter max-w-3xl flex gap-2.5",
                msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
              )}
            >
              {/* Avatar */}
              <div className="mt-1">
                {msg.role === "user" ? <UserAvatar /> : <AgentAvatar name={msg.agent_name} />}
              </div>

              {/* Bubble */}
              <div className="flex-1 min-w-0">
                {msg.role !== "user" && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-1 px-1 font-medium">
                    {msg.agent_name || "Istara"}
                  </p>
                )}
                <div
                  className={cn(
                    "rounded-2xl px-4 py-3",
                    msg.role === "user"
                      ? "bg-istara-600 text-white rounded-br-md"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-bl-md"
                  )}
                >
                  {msg.role === "user" ? (
                    <div className="whitespace-pre-wrap text-sm">{msg.content}</div>
                  ) : (
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({ children }) => {
                            const text = String(children);
                            if (text.startsWith("[Tool:") && text.endsWith("]")) {
                              const toolName = text.slice(7, -1);
                              return (
                                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 my-1 rounded-full bg-slate-200 dark:bg-slate-700 text-xs font-medium text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-600">
                                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                                  <span>Ran: <span className="font-bold">{toolName}</span></span>
                                </div>
                              );
                            }
                            return <p className="my-1">{children}</p>;
                          }
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                  )}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
                      <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Sources:</p>
                      {msg.sources.map((src, i) => (
                        <span
                          key={i}
                          className="inline-block text-xs bg-slate-200 dark:bg-slate-700 rounded px-1.5 py-0.5 mr-1 mb-1"
                        >
                          {(src.source ?? "unknown").split("/").pop()} ({Math.round((src.score ?? 0) * 100)}%)
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-1 px-1">
                  {formatDate(msg.created_at)}
                </p>
              </div>
            </div>
          ))}

          {/* Streaming response */}
          {streaming && streamingContent && (() => {
            const agentId = activeSession?.agent_id;
            const streamAgent = agentId ? agents.find((a) => a.id === agentId) : undefined;
            const streamAgentName = streamAgent?.name || "Istara";
            return (
            <div className="mr-auto max-w-3xl flex gap-2.5 message-enter">
              <div className="mt-1"><AgentAvatar name={streamAgentName} /></div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-1 px-1 font-medium">{streamAgentName}</p>
                <div className="rounded-2xl rounded-bl-md px-4 py-3 bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100">
                  <div className="streaming-cursor">
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({ children }) => {
                          const text = String(children);
                          if (text.startsWith("[Tool:") && text.endsWith("]")) {
                            const toolName = text.slice(7, -1);
                            return (
                              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 my-1 rounded-full bg-istara-100 dark:bg-istara-900/40 text-xs font-medium text-istara-700 dark:text-istara-300 border border-istara-200 dark:border-istara-800">
                                <Loader2 size={12} className="animate-spin text-istara-600 dark:text-istara-400" />
                                <span>⚡ Running: <span className="font-bold">{toolName}</span></span>
                              </div>
                            );
                          }
                          return <p className="my-1">{children}</p>;
                        }
                      }}
                    >
                      {streamingContent}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            </div>
            );
          })()}

          {streaming && !streamingContent && (() => {
            const agentId = activeSession?.agent_id;
            const thinkAgent = agentId ? agents.find((a) => a.id === agentId) : undefined;
            const thinkAgentName = thinkAgent?.name || "Istara";
            return (
            <div className="mr-auto flex items-center gap-2.5 text-slate-400 px-4">
              <div className="mt-0"><AgentAvatar name={thinkAgentName} /></div>
              <Loader2 size={16} className="animate-spin" />
              <span className="text-sm">Thinking...</span>
              <button
                onClick={cancelStreaming}
                className="ml-2 flex items-center gap-1 text-xs text-red-400 hover:text-red-500"
                aria-label="Cancel response"
              >
                <StopCircle size={12} /> Cancel
              </button>
            </div>
            );
          })()}

          {streaming && streamingContent && (
            <div className="flex justify-center">
              <button
                onClick={cancelStreaming}
                className="flex items-center gap-1 px-3 py-1 text-xs text-red-400 hover:text-red-500 bg-red-50 dark:bg-red-900/20 rounded-full"
                aria-label="Stop generating"
              >
                <StopCircle size={12} /> Stop generating
              </button>
            </div>
          )}

          {error && (
            <div className="mr-auto max-w-3xl">
              <div className="rounded-2xl px-4 py-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
                {error}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-slate-200 dark:border-slate-800 p-4">
          <div className="max-w-3xl mx-auto">
            {chatUnavailable && (
              <p role="status" className="mb-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                Chat is unavailable until a connected model is ready. Configure one in Settings.
              </p>
            )}
            {/* Queue status */}
            {capabilities.canUseSteering && (
              <SteeringQueueIndicator
                agentId={activeSession?.agent_id || "istara-main"}
                projectId={activeProjectId}
                enabled={capabilities.canUseSteering}
              />
            )}
            
            {/* Pending file chips */}
            {(pendingFiles.length > 0 || pendingDocRefs.length > 0) && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {pendingFiles.map((f, i) => (
                  <span key={`file-${i}`} className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-istara-50 dark:bg-istara-900/20 text-istara-700 dark:text-istara-300 border border-istara-200 dark:border-istara-800 rounded-lg">
                    <Paperclip size={10} />
                    {f.name}
                    <button onClick={() => removePendingFile(i)} className="ml-0.5 text-slate-400 hover:text-red-500" aria-label={`Remove ${f.name}`}><X size={10} /></button>
                  </span>
                ))}
                {pendingDocRefs.map((d) => (
                  <span key={`doc-${d.id}`} className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 rounded-lg">
                    <FileText size={10} />
                    {d.title}
                    <button onClick={() => removePendingDocRef(d.id)} className="ml-0.5 text-slate-400 hover:text-red-500" aria-label={`Remove ${d.title}`}><X size={10} /></button>
                  </span>
                ))}
              </div>
            )}

            <div className="flex items-end gap-2">
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt,.csv,.md,.mp3,.wav,.mp4,.mov,.jpg,.jpeg,.png"
                multiple
                onChange={handleFileSelect}
                disabled={!canWrite}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={!canWrite}
                className="p-2.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                title={canWrite ? "Upload file" : "Viewers cannot upload files"}
                aria-label="Upload file"
              >
                <Paperclip size={20} />
              </button>
              <button
                onClick={openDocPicker}
                disabled={!canWrite}
                className="p-2.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                title={canWrite ? "Attach project document" : "Viewers cannot attach documents"}
                aria-label="Attach project document"
              >
                <FolderOpen size={20} />
              </button>

              <div className="flex-1 relative">
                <textarea
                  value={isRecording ? "Recording voice..." : isTranscribing ? "Transcribing..." : input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  disabled={!canWrite || isRecording || isTranscribing}
                  placeholder={canWrite ? "Ask about your research, or drop files here..." : "Viewer access is read-only. Chat is disabled."}
                  rows={1}
                  className={cn(
                    "w-full resize-none rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-istara-500 focus:border-transparent",
                    (!canWrite || isRecording || isTranscribing) && "italic text-slate-500 bg-slate-50 dark:bg-slate-900"
                  )}
                  style={{ minHeight: "44px", maxHeight: "120px" }}
                />
                {isRecording && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    <button 
                      onClick={cancelRecording}
                      className="text-xs text-slate-400 hover:text-red-500"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>

              {/* Voice recording button */}
              <button
                onClick={handleVoiceToggle}
                disabled={!canWrite || streaming || isTranscribing}
                aria-label={isRecording ? "Stop recording" : "Start recording"}
                className={cn(
                  "p-2.5 rounded-lg transition-colors",
                  isRecording 
                    ? "bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400 animate-pulse"
                    : isTranscribing
                    ? "bg-slate-100 dark:bg-slate-800 text-slate-300 cursor-not-allowed"
                    : !streaming
                    ? "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-300 cursor-not-allowed"
                )}
                title={!canWrite ? "Viewers cannot use voice input" : isRecording ? "Stop and Transcribe" : "Voice input"}
              >
                {isTranscribing ? <Loader2 size={20} className="animate-spin" /> : <Mic size={20} />}
              </button>

              <button
                onClick={handleSend}
                disabled={!canWrite || chatUnavailable || (!input.trim() && pendingFiles.length === 0 && pendingDocRefs.length === 0) || streaming}
              aria-label="Send message"
              className={cn(
                "p-2.5 rounded-lg transition-colors",
                (input.trim() || pendingFiles.length > 0 || pendingDocRefs.length > 0) && !streaming
                  ? "bg-istara-600 text-white hover:bg-istara-700"
                  : "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
              )}
            >
              <Send size={20} />
            </button>
          </div>

          {/* Document picker modal */}
          {showDocPicker && (
            <div className="mt-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg p-3 max-h-64 overflow-hidden flex flex-col">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-slate-700 dark:text-slate-300">Attach from Project</span>
                <button onClick={() => { setShowDocPicker(false); setPickerSearch(""); }} className="text-slate-400 hover:text-slate-600" aria-label="Close picker"><X size={14} /></button>
              </div>
              <input
                type="text"
                placeholder="Search documents..."
                value={pickerSearch}
                onChange={(e) => searchDocs(e.target.value)}
                className="w-full px-2.5 py-1.5 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 mb-2 focus:outline-none focus:ring-2 focus:ring-istara-500"
                autoFocus
                aria-label="Search project documents"
              />
              <div className="flex-1 overflow-y-auto space-y-0.5">
                {pickerLoading ? (
                  <p className="text-xs text-slate-400 text-center py-4">Loading...</p>
                ) : pickerDocs.length === 0 ? (
                  <p className="text-xs text-slate-400 text-center py-4">No documents found</p>
                ) : (
                  pickerDocs.map((doc) => (
                    <button
                      key={doc.id}
                      onClick={() => selectDocRef(doc)}
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-sm hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2 text-slate-700 dark:text-slate-300"
                    >
                      <FileText size={14} className="text-purple-500 flex-shrink-0" />
                      <span className="truncate">{doc.title || "Untitled"}</span>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
          </div>
        </div>
      </div>
    </div>
  );
}
