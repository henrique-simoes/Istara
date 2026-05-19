"use client";

import { create } from "zustand";
import type { ChatSession, InferencePresetConfig } from "@/lib/types";
import { sessions as sessionsApi } from "@/lib/api";

// Persist active sessions per project so switching projects cannot replay another
// project's chat into the current view.
const ACTIVE_SESSION_KEY_PREFIX = "istara-active-session:";

function activeSessionKey(projectId: string): string {
  return `${ACTIVE_SESSION_KEY_PREFIX}${projectId}`;
}

function getSavedSessionId(projectId: string): string | null {
  if (typeof window === "undefined") return null;
  try { return localStorage.getItem(activeSessionKey(projectId)); } catch { return null; }
}

function saveSessionId(projectId: string, id: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (id) localStorage.setItem(activeSessionKey(projectId), id);
    else localStorage.removeItem(activeSessionKey(projectId));
  } catch {}
}

interface SessionStore {
  projectId: string | null;
  sessions: ChatSession[];
  activeSessionId: string | null;
  presets: Record<string, InferencePresetConfig> | null;
  loading: boolean;
  /** Pending message to auto-send when ChatView mounts (set by "Send to Agent" flow) */
  pendingPrefill: string | null;

  fetchSessions: (projectId: string) => Promise<void>;
  createSession: (projectId: string, title?: string, agentId?: string) => Promise<ChatSession>;
  selectSession: (projectId: string, id: string | null) => void;
  setPendingPrefill: (message: string | null) => void;
  updateSession: (projectId: string, id: string, data: Record<string, unknown>) => Promise<void>;
  deleteSession: (projectId: string, id: string) => Promise<void>;
  toggleStar: (projectId: string, id: string) => Promise<void>;
  renameSession: (projectId: string, id: string, title: string) => Promise<void>;
  ensureDefault: (projectId: string) => Promise<ChatSession>;
  fetchPresets: () => Promise<void>;

  activeSession: () => ChatSession | undefined;
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  projectId: null,
  sessions: [],
  activeSessionId: null,
  presets: null,
  loading: false,
  pendingPrefill: null,

  fetchSessions: async (projectId) => {
    const isProjectSwitch = get().projectId !== projectId;
    set(
      isProjectSwitch
        ? { projectId, sessions: [], activeSessionId: null, loading: true }
        : { projectId, loading: true }
    );
    try {
      const sessions = (await sessionsApi.list(projectId)).filter((session) => session.project_id === projectId);
      // Restore saved session if it exists in the fetched project list;
      // otherwise auto-select the most recent session so the UI never shows empty.
      const current = get().activeSessionId;
      const hasCurrent = !isProjectSwitch && current && sessions.some((s) => s.id === current);
      const savedId = getSavedSessionId(projectId);
      const hasSaved = savedId && sessions.some((s) => s.id === savedId);
      let resolvedId: string | null = null;
      if (hasCurrent) {
        resolvedId = current;
      } else if (hasSaved) {
        resolvedId = savedId;
      } else if (sessions.length > 0) {
        resolvedId = sessions[0].id;
      }
      saveSessionId(projectId, resolvedId);
      set({
        sessions,
        loading: false,
        activeSessionId: resolvedId,
      });
    } catch {
      if (isProjectSwitch) saveSessionId(projectId, null);
      set(
        isProjectSwitch
          ? { sessions: [], activeSessionId: null, loading: false }
          : { loading: false }
      );
    }
  },

  createSession: async (projectId, title, agentId) => {
    const session = await sessionsApi.create({
      project_id: projectId,
      title: title || "New Chat",
      agent_id: agentId,
    });
    saveSessionId(projectId, session.id);
    set((s) => ({
      projectId,
      sessions: [session, ...s.sessions.filter((existing) => existing.project_id === projectId && existing.id !== session.id)],
      activeSessionId: session.id,
    }));
    return session;
  },

  selectSession: (projectId, id) => {
    saveSessionId(projectId, id);
    set({ projectId, activeSessionId: id });
  },

  setPendingPrefill: (message) => set({ pendingPrefill: message }),

  updateSession: async (projectId, id, data) => {
    const updated = await sessionsApi.update(id, projectId, data);
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id && sess.project_id === projectId ? { ...sess, ...updated } : sess
      ),
    }));
  },

  deleteSession: async (projectId, id) => {
    await sessionsApi.delete(id, projectId);
    set((s) => {
      const newActiveId = s.activeSessionId === id ? null : s.activeSessionId;
      saveSessionId(projectId, newActiveId);
      return {
        sessions: s.sessions.filter((sess) => !(sess.id === id && sess.project_id === projectId)),
        activeSessionId: newActiveId,
      };
    });
  },

  toggleStar: async (projectId, id) => {
    const result = await sessionsApi.star(id, projectId);
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id && sess.project_id === projectId ? { ...sess, starred: result.starred } : sess
      ),
    }));
  },

  renameSession: async (projectId, id, title) => {
    await sessionsApi.update(id, projectId, { title });
    set((s) => ({
      sessions: s.sessions.map((sess) =>
        sess.id === id && sess.project_id === projectId ? { ...sess, title } : sess
      ),
    }));
  },

  ensureDefault: async (projectId) => {
    const session = await sessionsApi.ensureDefault(projectId);
    set((s) => {
      const projectSessions = s.sessions.filter((sess) => sess.project_id === projectId);
      const exists = projectSessions.some((sess) => sess.id === session.id);
      const savedId = getSavedSessionId(projectId);
      const hasCurrent = s.activeSessionId && projectSessions.some((sess) => sess.id === s.activeSessionId);
      const hasSaved = savedId && projectSessions.some((sess) => sess.id === savedId);
      const newActiveId = hasCurrent ? s.activeSessionId : hasSaved ? savedId : session.id;
      saveSessionId(projectId, newActiveId);
      return {
        projectId,
        sessions: exists ? projectSessions : [session, ...projectSessions],
        activeSessionId: newActiveId,
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
    const { sessions, activeSessionId, projectId } = get();
    return sessions.find((s) => s.id === activeSessionId && (!projectId || s.project_id === projectId));
  },
}));
