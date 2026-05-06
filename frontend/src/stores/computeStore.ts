/** Compute Pool store — tracks relay nodes and distributed capacity. */

import { create } from "zustand";

import { compute } from "@/lib/api";

interface ModelCapability {
  supports_tools: boolean;
  supports_vision: boolean;
  supports_audio?: boolean;
  supports_json?: boolean;
  parameter_count: string | null;
  context_length: number | null;
  trained_context_length?: number | null;
  loaded_context_length?: number | null;
  quantization?: string | null;
  is_loaded?: boolean | null;
  source?: string | null;
  endpoint_family?: string | null;
}

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
  source?: "local" | "network" | "relay" | "browser";
  host?: string;
  health_error?: string;
  serving_state?: string;
  capability_probe_status?: "available" | "unavailable" | "not_applicable";
  model_list_stale?: boolean;
  model_capabilities?: Record<string, ModelCapability>;
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
  request_slots_total?: number;
  request_slots_used?: number;
  request_slots_available?: number;
  request_slot_utilization_pct?: number;
  saturated_nodes?: number;
  hardware_load_pct?: number;
}

interface ComputeState {
  stats: ComputeStats | null;
  loading: boolean;
  error: string | null;
  fetchStats: () => Promise<void>;
  fetchNodes: () => Promise<void>;
}

export const useComputeStore = create<ComputeState>((set) => ({
  stats: null,
  loading: false,
  error: null,

  fetchStats: async () => {
    set({ loading: true, error: null });
    try {
      const data = await compute.stats();
      set({ stats: data, loading: false, error: null });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Could not load compute stats",
      });
    }
  },

  fetchNodes: async () => {
    set({ loading: true, error: null });
    try {
      const data = await compute.nodes();
      set({ stats: data, loading: false, error: null });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Could not load compute nodes",
      });
    }
  },
}));
