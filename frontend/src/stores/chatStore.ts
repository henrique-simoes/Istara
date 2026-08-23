"use client";

import { create } from "zustand";
import type { ChatMessage, ChatUsage, ThinkingMode } from "@/lib/types";
import { chat as chatApi, sessions as sessionsApi } from "@/lib/api";
import { useAgentStore } from "@/stores/agentStore";
import { useSessionStore } from "@/stores/sessionStore";

interface ChatStore {
  messages: ChatMessage[];
  streaming: boolean;
  streamingContent: string;
  error: string | null;
  usage: ChatUsage | null;
  abortController: AbortController | null;

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
  error: null,
  usage: null,
  abortController: null,

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
      set({ usage });
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
      error: null,
    }));

    try {
      let fullContent = "";
      let messageId = "";
      let sources: any[] = [];

      const activeThinkingMode = thinkingMode || useSessionStore.getState().activeSession()?.thinking_mode;
      for await (const event of chatApi.send(
        projectId,
        content,
        sessionId,
        controller.signal,
        activeThinkingMode
      )) {
        if (event.type === "chunk") {
          fullContent += event.content;
          set({ streamingContent: fullContent });
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
          set({ error: event.message, streaming: false, abortController: null });
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
      };

      let usage = get().usage;
      try {
        usage = await chatApi.usage(projectId, sessionId);
      } catch {
        // Keep the streamed last-turn telemetry if the aggregate request fails.
      }
      set((s) => ({
        messages: [...s.messages, assistantMsg],
        usage,
        streaming: false,
        streamingContent: "",
        abortController: null,
      }));
      void useSessionStore.getState().fetchSessions(projectId);
    } catch (e: any) {
      if (e.name === "AbortError") {
        set({ streaming: false, streamingContent: "", abortController: null });
        return;
      }
      set({ error: e.message, streaming: false, streamingContent: "", abortController: null });
    }
  },

  cancelStreaming: () => {
    const { abortController } = get();
    if (abortController) {
      abortController.abort();
      set({ streaming: false, streamingContent: "", abortController: null });
    }
  },

  clearMessages: () => set({ messages: [], streamingContent: "", error: null, usage: null }),
}));
