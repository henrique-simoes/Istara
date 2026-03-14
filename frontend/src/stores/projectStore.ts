"use client";

import { create } from "zustand";
import type { Project } from "@/lib/types";
import { projects as projectsApi } from "@/lib/api";

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

  activeProject: () => Project | undefined;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  projects: [],
  activeProjectId: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const data = await projectsApi.list();
      set({ projects: data, loading: false });
      // Auto-select first project if none selected
      if (!get().activeProjectId && data.length > 0) {
        set({ activeProjectId: data[0].id });
      }
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  setActiveProject: (id) => set({ activeProjectId: id }),

  createProject: async (name, description) => {
    const project = await projectsApi.create({ name, description });
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
    set((s) => ({
      projects: s.projects.filter((p) => p.id !== id),
      activeProjectId: s.activeProjectId === id ? null : s.activeProjectId,
    }));
  },

  activeProject: () => {
    const state = get();
    return state.projects.find((p) => p.id === state.activeProjectId);
  },
}));
