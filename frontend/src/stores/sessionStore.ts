"use client";

import { create } from "zustand";
import type { ChatSession, InferencePreset, InferencePresetConfig } from "@/lib/types";
import { sessions as sessionsApi } from "@/lib/api";

interface SessionStore {
  sessions: ChatSession[];
  activeSessionId: string | null;
  presets: Record<string, InferencePresetConfig> | null;
  loading: boolean;
  /** Pending message to auto-send when ChatView mounts (set by "Send to Agent" flow) */
  pendingPrefill: string | null;

  fetchSessions: (projectId: string) => Promise<void>;
  createSession: (projectId: string, title?: string, agentId?: string) => Promise<ChatSession>;
  selectSession: (id: string | null) => void;
  setPendingPrefill: (message: string | null) => void;
  updateSession: (id: string, data: Record<string, unknown>) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  toggleStar: (id: string) => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
  ensureDefault: (projectId: string) => Promise<ChatSession>;
  fetchPresets: () => Promise<void>;

  activeSession: () => ChatSession | undefined;
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  presets: null,
  loading: false,
  pendingPrefill: null,

  fetchSessions: async (projectId) => {
    set({ loading: true });
    try {
      const sessions = await sessionsApi.list(projectId);
      set({ sessions, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  createSession: async (projectId, title, agentId) => {
    const session = await sessionsApi.create({
      project_id: projectId,
      title: title || "New Chat",
      agent_id: agentId,
    });
    set((s) => ({ sessions: [session, ...s.sessions], activeSessionId: session.id }));
    return session;
  },

  selectSession: (id) => set({ activeSessionId: id }),

  setPendingPrefill: (message) => set({ pendingPrefill: message }),

  updateSession: async (id, data) => {
    const updated = await sessionsApi.update(id, data);
    set((s) => ({
      sessions: s.sessions.map((sess) => (sess.id === id ? { ...sess, ...updated } : sess)),
    }));
  },

  deleteSession: async (id) => {
    await sessionsApi.delete(id);
    set((s) => ({
      sessions: s.sessions.filter((sess) => sess.id !== id),
      activeSessionId: s.activeSessionId === id ? null : s.activeSessionId,
    }));
  },

  toggleStar: async (id) => {
    const result = await sessionsApi.star(id);
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id ? { ...sess, starred: result.starred } : sess
      ),
    }));
  },

  renameSession: async (id, title) => {
    await sessionsApi.update(id, { title });
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id ? { ...sess, title } : sess
      ),
    }));
  },

  ensureDefault: async (projectId) => {
    const session = await sessionsApi.ensureDefault(projectId);
    set((s) => {
      const exists = s.sessions.some((sess) => sess.id === session.id);
      return {
        sessions: exists ? s.sessions : [session, ...s.sessions],
        activeSessionId: s.activeSessionId || session.id,
      };
    });
    return session;
  },

  fetchPresets: async () => {
    try {
      const presets = await sessionsApi.presets();
      set({ presets });
    } catch {
      // silent
    }
  },

  activeSession: () => {
    const { sessions, activeSessionId } = get();
    return sessions.find((s) => s.id === activeSessionId);
  },
}));
