"use client";

import { create } from "zustand";
import { loops as loopsApi } from "@/lib/api";
import type { LoopExecution, AgentLoopConfig, LoopHealthItem, ScheduledLoop } from "@/lib/types";

type LoopsTab = "overview" | "schedules" | "agent-loops" | "custom" | "history";

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
  schedules: ScheduledLoop[];
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
  fetchSchedules: (projectId?: string) => Promise<void>;
  createSchedule: (data: {
    name: string;
    skill_name?: string;
    project_id: string;
    cron_expression: string;
    description?: string;
  }) => Promise<void>;
  updateSchedule: (scheduleId: string, data: Record<string, unknown>) => Promise<void>;
  deleteSchedule: (scheduleId: string) => Promise<void>;
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

  fetchSchedules: async (projectId) => {
    set({ loading: true, error: null });
    try {
      const data = await loopsApi.schedules(projectId ? { project_id: projectId } : undefined);
      const schedules = Array.isArray(data) ? data : data?.schedules || [];
      set({ schedules, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  createSchedule: async (data) => {
    set({ loading: true, error: null });
    try {
      await loopsApi.createSchedule(data);
      set({ loading: false });
      await get().fetchSchedules();
      await get().fetchHealth();
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  updateSchedule: async (scheduleId, data) => {
    set({ error: null });
    try {
      await loopsApi.updateSchedule(scheduleId, data);
      await get().fetchSchedules();
      await get().fetchHealth();
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  deleteSchedule: async (scheduleId) => {
    set({ error: null });
    try {
      await loopsApi.deleteSchedule(scheduleId);
      await get().fetchSchedules();
      await get().fetchHealth();
    } catch (e: any) {
      set({ error: e.message });
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
      const totalPages = data?.total_pages || Math.max(1, Math.ceil((data?.total || 0) / (data?.page_size || 20)));
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
      await get().fetchHealth();
      await get().fetchSchedules();
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
