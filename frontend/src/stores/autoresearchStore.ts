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
  fetchStatus: () => Promise<void>;
  fetchExperiments: (params?: {
    loop_type?: string;
    kept?: boolean;
    limit?: number;
    offset?: number;
  }) => Promise<void>;
  fetchLeaderboard: () => Promise<void>;
  fetchConfig: () => Promise<void>;
  startLoop: (data: {
    loop_type: string;
    target: string;
    max_iterations?: number;
    project_id?: string;
  }) => Promise<void>;
  stopLoop: () => Promise<void>;
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

  fetchStatus: async () => {
    try {
      const status = await autoresearch.status();
      set({ status });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  fetchExperiments: async (params) => {
    set({ loading: true });
    try {
      const data = await autoresearch.experiments(params);
      set({ experiments: Array.isArray(data) ? data : [], loading: false });
    } catch (e: any) {
      set({ loading: false, error: e.message });
    }
  },

  fetchLeaderboard: async () => {
    set({ loading: true });
    try {
      const data = await autoresearch.leaderboard();
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
      await get().fetchStatus();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  stopLoop: async () => {
    set({ error: null });
    try {
      await autoresearch.stop();
      await get().fetchStatus();
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
      await get().fetchStatus();
      await get().fetchConfig();
    } catch (e: any) {
      set({ error: e.message });
    }
  },
}));
