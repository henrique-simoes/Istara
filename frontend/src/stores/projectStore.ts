"use client";

import { create } from "zustand";
import type { Project } from "@/lib/types";
import { projects as projectsApi } from "@/lib/api";

// Persist activeProjectId to localStorage so it survives page refreshes
const PROJECT_KEY = "reclaw-active-project";

function getSavedProjectId(): string | null {
  if (typeof window === "undefined") return null;
  try { return localStorage.getItem(PROJECT_KEY); } catch { return null; }
}

function saveProjectId(id: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (id) localStorage.setItem(PROJECT_KEY, id);
    else localStorage.removeItem(PROJECT_KEY);
  } catch {}
}

interface ProjectStore {
  projects: Project[];
  activeProjectId: string | null;
  loading: boolean;
  error: string | null;

  fetchProjects: () => Promise<void>;
  setActiveProject: (id: string | null) => void;
  createProject: (name: string, description?: string) => Promise<Project>;
  updateProject: (id: string, data: Record<string, unknown>) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  pauseProject: (id: string) => Promise<void>;
  resumeProject: (id: string) => Promise<void>;

  activeProject: () => Project | undefined;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  projects: [],
  activeProjectId: getSavedProjectId(),
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const data = await projectsApi.list();
      set({ projects: data, loading: false });
      // Restore saved project if it exists in the fetched list; fallback to first.
      // CRITICAL: clear stale ID when no projects exist or saved ID is orphaned.
      const current = get().activeProjectId;
      const hasCurrent = current && data.some((p) => p.id === current);
      if (!hasCurrent) {
        if (data.length > 0) {
          saveProjectId(data[0].id);
          set({ activeProjectId: data[0].id });
        } else {
          // No projects at all — clear any stale ID
          saveProjectId(null);
          set({ activeProjectId: null });
        }
      }
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  setActiveProject: (id) => {
    saveProjectId(id);
    set({ activeProjectId: id });
  },

  createProject: async (name, description) => {
    const project = await projectsApi.create({ name, description });
    saveProjectId(project.id);
    set((s) => ({
      projects: [project, ...s.projects],
      activeProjectId: project.id,
    }));
    return project;
  },

  updateProject: async (id, data) => {
    const updated = await projectsApi.update(id, data);
    set((s) => ({
      projects: s.projects.map((p) => (p.id === id ? updated : p)),
    }));
  },

  deleteProject: async (id) => {
    await projectsApi.delete(id);
    set((s) => {
      const newActiveId = s.activeProjectId === id ? null : s.activeProjectId;
      saveProjectId(newActiveId);
      return {
        projects: s.projects.filter((p) => p.id !== id),
        activeProjectId: newActiveId,
      };
    });
  },

  pauseProject: async (id: string) => {
    await projectsApi.pause(id);
    set((s) => ({
      projects: s.projects.map((p) =>
        p.id === id ? { ...p, is_paused: true } : p
      ),
    }));
  },

  resumeProject: async (id: string) => {
    await projectsApi.resume(id);
    set((s) => ({
      projects: s.projects.map((p) =>
        p.id === id ? { ...p, is_paused: false } : p
      ),
    }));
  },

  activeProject: () => {
    const state = get();
    return state.projects.find((p) => p.id === state.activeProjectId);
  },
}));
