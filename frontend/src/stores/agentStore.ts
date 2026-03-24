"use client";

import { create } from "zustand";
import type { Agent, A2AMessage, AgentCapacityCheck, HeartbeatStatus } from "@/lib/types";
import { agents as agentsApi } from "@/lib/api";

const POLL_INTERVAL_MS = 10_000;

interface AgentStore {
  agents: Agent[];
  selectedAgentId: string | null;
  loading: boolean;
  error: string | null;
  a2aMessages: A2AMessage[];
  capacity: AgentCapacityCheck | null;
  _pollTimer: ReturnType<typeof setInterval> | null;

  fetchAgents: () => Promise<void>;
  startPolling: () => void;
  stopPolling: () => void;
  updateAgentStatus: (agentId: string, state: string, currentTask?: string) => void;
  selectAgent: (id: string | null) => void;
  createAgent: (data: {
    name: string;
    role?: string;
    system_prompt?: string;
    capabilities?: string[];
    heartbeat_interval?: number;
  }) => Promise<Agent>;
  updateAgent: (id: string, data: Record<string, unknown>) => Promise<void>;
  deleteAgent: (id: string) => Promise<void>;
  pauseAgent: (id: string) => Promise<void>;
  resumeAgent: (id: string) => Promise<void>;
  fetchA2ALog: () => Promise<void>;
  fetchCapacity: () => Promise<void>;
  updateHeartbeat: (agentId: string, status: HeartbeatStatus) => void;

  selectedAgent: () => Agent | undefined;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  agents: [],
  selectedAgentId: null,
  loading: false,
  error: null,
  a2aMessages: [],
  capacity: null,
  _pollTimer: null,

  fetchAgents: async () => {
    set({ loading: true, error: null });
    try {
      const data = await agentsApi.list();
      set({ agents: data.agents || [], loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  startPolling: () => {
    const { _pollTimer, fetchAgents } = get();
    if (_pollTimer) return; // already polling
    const timer = setInterval(() => {
      fetchAgents();
    }, POLL_INTERVAL_MS);
    set({ _pollTimer: timer });
  },

  stopPolling: () => {
    const { _pollTimer } = get();
    if (_pollTimer) {
      clearInterval(_pollTimer);
      set({ _pollTimer: null });
    }
  },

  updateAgentStatus: (agentId, state, currentTask) => {
    set((s) => ({
      agents: s.agents.map((a) =>
        a.id === agentId
          ? { ...a, state: state as Agent["state"], ...(currentTask !== undefined ? { current_task: currentTask } : {}) }
          : a
      ),
    }));
  },

  selectAgent: (id) => set({ selectedAgentId: id }),

  createAgent: async (data) => {
    const agent = await agentsApi.create(data);
    set((s) => ({ agents: [...s.agents, agent] }));
    return agent;
  },

  updateAgent: async (id, data) => {
    const updated = await agentsApi.update(id, data);
    set((s) => ({
      agents: s.agents.map((a) => (a.id === id ? { ...a, ...updated } : a)),
    }));
  },

  deleteAgent: async (id) => {
    await agentsApi.delete(id);
    set((s) => ({
      agents: s.agents.filter((a) => a.id !== id),
      selectedAgentId: s.selectedAgentId === id ? null : s.selectedAgentId,
    }));
  },

  pauseAgent: async (id) => {
    await agentsApi.pause(id);
    set((s) => ({
      agents: s.agents.map((a) =>
        a.id === id ? { ...a, state: "paused" as const } : a
      ),
    }));
  },

  resumeAgent: async (id) => {
    await agentsApi.resume(id);
    set((s) => ({
      agents: s.agents.map((a) =>
        a.id === id ? { ...a, state: "idle" as const } : a
      ),
    }));
  },

  fetchA2ALog: async () => {
    try {
      const data = await agentsApi.a2aLog();
      set({ a2aMessages: data.messages || [] });
    } catch {
      // silent
    }
  },

  fetchCapacity: async () => {
    try {
      const cap = await agentsApi.capacity();
      set({ capacity: cap });
    } catch {
      // silent
    }
  },

  updateHeartbeat: (agentId, status) => {
    set((s) => ({
      agents: s.agents.map((a) =>
        a.id === agentId ? { ...a, heartbeat_status: status } : a
      ),
    }));
  },

  selectedAgent: () => {
    const { agents, selectedAgentId } = get();
    return agents.find((a) => a.id === selectedAgentId);
  },
}));
