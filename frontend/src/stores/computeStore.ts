/** Compute Pool store — tracks relay nodes and distributed capacity. */

import { create } from "zustand";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ComputeNode {
  node_id: string;
  hostname: string;
  state: string;
  ram_available_gb: number;
  cpu_load_pct: number;
  loaded_models: string[];
  score: number;
  latency_ms: number;
  alive: boolean;
}

interface ComputeStats {
  total_nodes: number;
  alive_nodes: number;
  total_ram_gb: number;
  available_ram_gb: number;
  total_cpu_cores: number;
  available_models: string[];
  nodes: ComputeNode[];
  swarm_tier?: string;
}

interface ComputeState {
  stats: ComputeStats | null;
  loading: boolean;
  fetchStats: () => Promise<void>;
  fetchNodes: () => Promise<void>;
}

export const useComputeStore = create<ComputeState>((set) => ({
  stats: null,
  loading: false,

  fetchStats: async () => {
    set({ loading: true });
    try {
      const res = await fetch(`${API_BASE}/api/compute/stats`);
      const data = await res.json();
      set({ stats: data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchNodes: async () => {
    set({ loading: true });
    try {
      const res = await fetch(`${API_BASE}/api/compute/nodes`);
      const data = await res.json();
      set({ stats: data, loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
