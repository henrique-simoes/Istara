"use client";

import { create } from "zustand";
import { loops as loopsApi } from "@/lib/api";
import type { LoopExecution, AgentLoopConfig, LoopHealthItem } from "@/lib/types";

type LoopsTab = "overview" | "schedules" | "agent-loops" | "custom" | "history";

interface Schedule {
  id: string;
  name: string;
  skill_name: string;
  project_id: string;
  cron_expression: string;
  interval_seconds: number | null;
  description: string;
  enabled: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  execution_count: number;
  created_at: string;
}

interface LoopsOverview {
  active_loops: number;
  paused_loops: number;
  behind_schedule: number;
  total_executions_24h: number;
  success_rate: number;
}

interface ExecutionStats {
  total: number;
  success: number;
  failure: number;
  running: number;
  avg_duration_ms: number;
}

interface LoopsStore {
  activeTab: LoopsTab;
  overview: LoopsOverview | null;
  agentLoops: AgentLoopConfig[];
  schedules: Schedule[];
  executions: LoopExecution[];
  health: LoopHealthItem[];
  stats: ExecutionStats | null;
  loading: boolean;
  error: string | null;
  executionPage: number;
  executionTotalPages: number;
  executionFilters: {
    source_type: string;
    status: string;
    from_date: string;
    to_date: string;
  };

  setActiveTab: (tab: LoopsTab) => void;
  fetchOverview: () => Promise<void>;
  fetchAgentLoops: () => Promise<void>;
  fetchAgentConfig: (agentId: string) => Promise<AgentLoopConfig | null>;
  updateAgentConfig: (agentId: string, data: Record<string, unknown>) => Promise<void>;
  pauseAgent: (agentId: string) => Promise<void>;
  resumeAgent: (agentId: string) => Promise<void>;
  fetchExecutions: (page?: number) => Promise<void>;
  fetchExecutionStats: (sourceId?: string) => Promise<void>;
  fetchHealth: () => Promise<void>;
  createCustomLoop: (data: {
    name: string;
    skill_name: string;
    project_id: string;
    cron_expression?: string;
    interval_seconds?: number;
    description?: string;
  }) => Promise<void>;
  setExecutionFilter: (key: string, value: string) => void;
}

export const useLoopsStore = create<LoopsStore>((set, get) => ({
  activeTab: "overview",
  overview: null,
  agentLoops: [],
  schedules: [],
  executions: [],
  health: [],
  stats: null,
  loading: false,
  error: null,
  executionPage: 1,
  executionTotalPages: 1,
  executionFilters: {
    source_type: "",
    status: "",
    from_date: "",
    to_date: "",
  },

  setActiveTab: (tab) => set({ activeTab: tab }),

  fetchOverview: async () => {
    set({ loading: true, error: null });
    try {
      const data = await loopsApi.overview();
      set({ overview: data, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  fetchAgentLoops: async () => {
    set({ loading: true, error: null });
    try {
      const data = await loopsApi.agents();
      const configs = Array.isArray(data) ? data : data?.configs || data?.agents || [];
      set({ agentLoops: configs, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  fetchAgentConfig: async (agentId) => {
    try {
      const data = await loopsApi.agentConfig(agentId);
      return data as AgentLoopConfig;
    } catch {
      return null;
    }
  },

  updateAgentConfig: async (agentId, data) => {
    try {
      await loopsApi.updateAgentConfig(agentId, data);
      // Refresh agent loops
      get().fetchAgentLoops();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  pauseAgent: async (agentId) => {
    try {
      await loopsApi.pauseAgent(agentId);
      get().fetchAgentLoops();
      get().fetchHealth();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  resumeAgent: async (agentId) => {
    try {
      await loopsApi.resumeAgent(agentId);
      get().fetchAgentLoops();
      get().fetchHealth();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  fetchExecutions: async (page = 1) => {
    set({ loading: true, error: null });
    try {
      const filters = get().executionFilters;
      const params: Record<string, string | number> = { page, page_size: 20 };
      if (filters.source_type) params.source_type = filters.source_type;
      if (filters.status) params.status = filters.status;
      if (filters.from_date) params.from_date = filters.from_date;
      if (filters.to_date) params.to_date = filters.to_date;
      const data = await loopsApi.executions(params);
      const executions = Array.isArray(data) ? data : data?.executions || [];
      const totalPages = data?.total_pages || 1;
      set({ executions, executionPage: page, executionTotalPages: totalPages, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  fetchExecutionStats: async (sourceId) => {
    try {
      const data = await loopsApi.executionStats(sourceId);
      set({ stats: data });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  fetchHealth: async () => {
    set({ loading: true, error: null });
    try {
      const data = await loopsApi.health();
      const items = Array.isArray(data) ? data : data?.items || data?.health || [];
      set({ health: items, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  createCustomLoop: async (data) => {
    set({ loading: true, error: null });
    try {
      await loopsApi.createCustom(data);
      set({ loading: false });
      get().fetchHealth();
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  setExecutionFilter: (key, value) => {
    set((s) => ({
      executionFilters: { ...s.executionFilters, [key]: value },
    }));
  },
}));
