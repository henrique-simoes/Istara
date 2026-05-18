"use client";

import { create } from "zustand";
import { autoresearch } from "@/lib/api";
import type {
  AutoresearchExperiment,
  AutoresearchConfig,
  AutoresearchStatus,
  ModelSkillLeaderboard,
} from "@/lib/types";

type AutoresearchTab = "dashboard" | "experiments" | "leaderboard" | "config";

interface AutoresearchStore {
  activeTab: AutoresearchTab;
  status: AutoresearchStatus | null;
  experiments: AutoresearchExperiment[];
  leaderboard: ModelSkillLeaderboard[];
  config: AutoresearchConfig | null;
  loading: boolean;
  error: string | null;

  setActiveTab: (tab: AutoresearchTab) => void;
  fetchStatus: (projectId: string | null) => Promise<void>;
  fetchExperiments: (params?: {
    project_id?: string | null;
    loop_type?: string;
    kept?: boolean;
    limit?: number;
    offset?: number;
  }) => Promise<void>;
  fetchLeaderboard: (projectId: string | null) => Promise<void>;
  fetchConfig: () => Promise<void>;
  startLoop: (data: {
    loop_type: string;
    target: string;
    max_iterations?: number;
    project_id?: string;
  }) => Promise<void>;
  stopLoop: (projectId: string | null) => Promise<void>;
  updateConfig: (data: Record<string, any>) => Promise<void>;
  toggle: (enabled: boolean) => Promise<void>;
}

export const useAutoresearchStore = create<AutoresearchStore>((set, get) => ({
  activeTab: "dashboard",
  status: null,
  experiments: [],
  leaderboard: [],
  config: null,
  loading: false,
  error: null,

  setActiveTab: (tab) => set({ activeTab: tab }),

  fetchStatus: async (projectId) => {
    if (!projectId) {
      set({ status: null });
      return;
    }
    try {
      const status = await autoresearch.status(projectId);
      set({ status });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  fetchExperiments: async (params) => {
    if (!params?.project_id) {
      set({ experiments: [] });
      return;
    }
    set({ loading: true });
    try {
      const data = await autoresearch.experiments({
        ...params,
        project_id: params.project_id,
      });
      set({ experiments: Array.isArray(data) ? data : [], loading: false });
    } catch (e: any) {
      set({ loading: false, error: e.message });
    }
  },

  fetchLeaderboard: async (projectId) => {
    if (!projectId) {
      set({ leaderboard: [] });
      return;
    }
    set({ loading: true });
    try {
      const data = await autoresearch.leaderboard(projectId);
      set({ leaderboard: Array.isArray(data) ? data : [], loading: false });
    } catch (e: any) {
      set({ loading: false, error: e.message });
    }
  },

  fetchConfig: async () => {
    try {
      const config = await autoresearch.config();
      set({ config });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  startLoop: async (data) => {
    set({ error: null });
    try {
      await autoresearch.start(data);
      await get().fetchStatus(data.project_id || null);
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  stopLoop: async (projectId) => {
    set({ error: null });
    try {
      if (!projectId) return;
      await autoresearch.stop(projectId);
      await get().fetchStatus(projectId);
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  updateConfig: async (data) => {
    try {
      const config = await autoresearch.updateConfig(data);
      set({ config });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  toggle: async (enabled) => {
    try {
      await autoresearch.toggle(enabled);
      const projectId = get().status?.current_experiment?.project_id || null;
      await get().fetchStatus(projectId);
      await get().fetchConfig();
    } catch (e: any) {
      set({ error: e.message });
    }
  },
}));
