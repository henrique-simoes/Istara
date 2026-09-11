"use client";

import { create } from "zustand";
import type { ChatMessage, ChatUsage, ThinkingMode, ToolCallExecution } from "@/lib/types";
import { chat as chatApi, sessions as sessionsApi } from "@/lib/api";
import { useAgentStore } from "@/stores/agentStore";
import { useSessionStore } from "@/stores/sessionStore";

interface ChatStore {
  messages: ChatMessage[];
  streaming: boolean;
  streamingContent: string;
  streamingThoughts: string[];
  streamingToolCalls: ToolCallExecution[];
  activeStreamingTool: string | null;
  error: string | null;
  usage: ChatUsage | null;
  abortController: AbortController | null;
  // null = catalog unknown (fetch failed): send NO engine header so the
  // backend falls back to the persisted project/global choice (F-B1).
  engine: "pi" | "legacy" | null;

  setEngine: (engine: "pi" | "legacy" | null) => void;

  fetchHistory: (projectId: string, sessionId?: string) => Promise<void>;
  sendMessage: (
    projectId: string,
    content: string,
    sessionId?: string,
    thinkingMode?: ThinkingMode
  ) => Promise<void>;
  cancelStreaming: () => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  streaming: false,
  streamingContent: "",
  streamingThoughts: [],
  streamingToolCalls: [],
  activeStreamingTool: null,
  error: null,
  usage: null,
  abortController: null,
  engine: null,

  setEngine: (engine) => set({ engine }),

  fetchHistory: async (projectId, sessionId) => {
    set({ messages: [], streamingContent: "", error: null, usage: null });
    try {
      if (sessionId) {
        // Fetch session-scoped messages
        const detail = await sessionsApi.get(sessionId, projectId);
        const msgs: ChatMessage[] = (detail.messages || []).map((m: any) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          created_at: m.created_at,
          agent_id: m.agent_id,
          agent_name: m.agent_name,
        }));
        set({ messages: msgs, error: null });
      } else {
        const history = await chatApi.history(projectId);
        set({ messages: history, error: null });
      }
    } catch (e: any) {
      set({ messages: [], error: e.message });
    }
    try {
      const usage = await chatApi.usage(projectId, sessionId);
      const hydrated = usage.latest ? {
        ...usage,
        last_turn: {
          usage: {
            input_tokens: usage.latest.input_tokens,
            output_tokens: usage.latest.output_tokens || 0,
            cacheRead: usage.latest.cache_read || 0,
            cacheWrite: usage.latest.cache_write || 0,
            totalTokens: usage.latest.total_tokens || 0,
            cost: { total: usage.latest.cost_usd || 0 },
          },
          model: usage.latest.model,
          endpoint_id: usage.latest.endpoint_id,
          stop_reason: usage.latest.stop_reason,
        },
      } : usage;
      set({ usage: hydrated });
    } catch {
      // Older servers may not expose the additive usage endpoint yet.
      set({ usage: null });
    }
  },

  sendMessage: async (projectId, content, sessionId, thinkingMode) => {
    // Cancel any existing stream first
    const existing = get().abortController;
    if (existing) {
      existing.abort();
    }

    // Add user message immediately
    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    const controller = new AbortController();
    set({ abortController: controller });

    set((s) => ({
      messages: [...s.messages, userMsg],
      streaming: true,
      streamingContent: "",
      streamingThoughts: [],
      streamingToolCalls: [],
      activeStreamingTool: null,
      error: null,
    }));

    try {
      let fullContent = "";
      let messageId = "";
      let sources: any[] = [];
      const thoughts: string[] = [];
      const toolCalls: ToolCallExecution[] = [];

      const activeThinkingMode = thinkingMode || useSessionStore.getState().activeSession()?.thinking_mode;
      for await (const event of chatApi.send(
        projectId,
        content,
        sessionId,
        controller.signal,
        activeThinkingMode,
        get().engine ?? undefined
      )) {
        if (event.type === "chunk") {
          fullContent += event.content;
          set({ streamingContent: fullContent, activeStreamingTool: null });
        } else if (event.type === "thought" || event.type === "thinking") {
          const thoughtChunk = event.content || event.text || "";
          if (thoughtChunk) {
            thoughts.push(thoughtChunk);
            set({ streamingThoughts: [...thoughts] });
          }
        } else if (event.type === "tool_call") {
          const toolName = event.tool || event.name || "tool";
          const callId = event.tool_call_id || `tc-${Date.now()}-${toolCalls.length}`;
          const existing = toolCalls.find((t) => t.id === callId);
          if (!existing) {
            const newCall: ToolCallExecution = {
              id: callId,
              tool: toolName,
              params: event.params || {},
              status: "running",
            };
            toolCalls.push(newCall);
          }
          set({
            streamingToolCalls: [...toolCalls],
            activeStreamingTool: toolName,
          });
        } else if (event.type === "tool_result") {
          const callId = event.tool_call_id;
          const toolName = event.tool;
          const target = toolCalls.find(
            (t) => (callId && t.id === callId) || (t.tool === toolName && t.status === "running")
          );
          if (target) {
            target.status = event.ok === false ? "error" : "completed";
            if (event.result !== undefined) {
              target.result = typeof event.result === "string" ? event.result : JSON.stringify(event.result);
            }
          } else if (toolName) {
            toolCalls.push({
              id: callId || `tc-${Date.now()}`,
              tool: toolName,
              result: event.result !== undefined ? (typeof event.result === "string" ? event.result : JSON.stringify(event.result)) : undefined,
              status: event.ok === false ? "error" : "completed",
            });
          }
          set({
            streamingToolCalls: [...toolCalls],
            activeStreamingTool: null,
          });
        } else if (event.type === "done") {
          messageId = event.message_id;
          sources = event.sources || [];
        } else if (event.type === "usage") {
          set((state) => ({
            usage: {
              ...(state.usage || {
                input_tokens: 0, output_tokens: 0, cache_read: 0, cache_write: 0,
                total_tokens: 0, cost_usd: 0, turns: 0, row_count: 0,
                exact: true, estimated: false,
              }),
              last_turn: {
                usage: event.usage || {},
                model: event.model || "",
                endpoint_id: event.endpoint_id,
                stop_reason: event.stop_reason,
                effort: event.effort,
              },
            },
          }));
        } else if (event.type === "error") {
          set({
            error: event.message,
            streaming: false,
            streamingThoughts: [],
            streamingToolCalls: [],
            activeStreamingTool: null,
            abortController: null,
          });
          return;
        }
      }

      // Resolve agent name from the active session's agent_id
      const activeSession = useSessionStore.getState().activeSession();
      const agentId = activeSession?.agent_id;
      const agentName = agentId
        ? useAgentStore.getState().agents.find((a) => a.id === agentId)?.name
        : undefined;

      // Add completed assistant message
      const assistantMsg: ChatMessage = {
        id: messageId || `msg-${Date.now()}`,
        role: "assistant",
        content: fullContent,
        created_at: new Date().toISOString(),
        sources,
        agent_id: agentId ?? undefined,
        agent_name: agentName,
        thoughts: thoughts.length > 0 ? thoughts : undefined,
        tool_calls: toolCalls.length > 0 ? toolCalls : undefined,
      };

      const streamedLastTurn = get().usage?.last_turn;
      let usage = get().usage;
      try {
        const aggregate = await chatApi.usage(projectId, sessionId);
        usage = streamedLastTurn ? { ...aggregate, last_turn: streamedLastTurn } : aggregate;
      } catch {
        // Keep the streamed last-turn telemetry if the aggregate request fails.
      }
      set((s) => ({
        messages: [...s.messages, assistantMsg],
        usage,
        streaming: false,
        streamingContent: "",
        streamingThoughts: [],
        streamingToolCalls: [],
        activeStreamingTool: null,
        abortController: null,
      }));
      void useSessionStore.getState().fetchSessions(projectId);
    } catch (e: any) {
      if (e.name === "AbortError") {
        set({
          streaming: false,
          streamingContent: "",
          streamingThoughts: [],
          streamingToolCalls: [],
          activeStreamingTool: null,
          abortController: null,
        });
        return;
      }
      set({
        error: e.message,
        streaming: false,
        streamingContent: "",
        streamingThoughts: [],
        streamingToolCalls: [],
        activeStreamingTool: null,
        abortController: null,
      });
    }
  },

  cancelStreaming: () => {
    const { abortController } = get();
    if (abortController) {
      abortController.abort();
      set({
        streaming: false,
        streamingContent: "",
        streamingThoughts: [],
        streamingToolCalls: [],
        activeStreamingTool: null,
        abortController: null,
      });
    }
  },

  clearMessages: () =>
    set({
      messages: [],
      streamingContent: "",
      streamingThoughts: [],
      streamingToolCalls: [],
      activeStreamingTool: null,
      error: null,
      usage: null,
    }),
}));
