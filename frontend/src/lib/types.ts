/** Core types for ReClaw frontend. */

export type ProjectPhase = "discover" | "define" | "develop" | "deliver";
export type TaskStatus = "backlog" | "in_progress" | "in_review" | "done";

export interface Project {
  id: string;
  name: string;
  description: string;
  phase: ProjectPhase;
  company_context: string;
  project_context: string;
  guardrails: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  skill_name: string;
  agent_notes: string;
  user_context: string;
  progress: number;
  position: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  sources?: { source: string; score: number; page?: number }[];
}

export interface Nugget {
  id: string;
  project_id: string;
  text: string;
  source: string;
  source_location: string;
  tags: string[];
  phase: string;
  confidence: number;
  created_at: string;
}

export interface Fact {
  id: string;
  project_id: string;
  text: string;
  nugget_ids: string[];
  phase: string;
  confidence: number;
  created_at: string;
}

export interface Insight {
  id: string;
  project_id: string;
  text: string;
  fact_ids: string[];
  phase: string;
  confidence: number;
  impact: string;
  created_at: string;
}

export interface Recommendation {
  id: string;
  project_id: string;
  text: string;
  insight_ids: string[];
  phase: string;
  priority: string;
  effort: string;
  status: string;
  created_at: string;
}

export interface FindingsSummary {
  project_id: string;
  totals: {
    nuggets: number;
    facts: number;
    insights: number;
    recommendations: number;
  };
  by_phase: Record<
    ProjectPhase,
    {
      nuggets: number;
      facts: number;
      insights: number;
      recommendations: number;
    }
  >;
}

export interface HardwareInfo {
  total_ram_gb: number;
  available_ram_gb: number;
  reclaw_ram_budget_gb: number;
  cpu_cores: number;
  cpu_arch: string;
  reclaw_cpu_budget_cores: number;
  gpu: { vendor: string; name: string; vram_mb: number } | null;
  os: string;
}

export interface ModelRecommendation {
  model_name: string;
  quantization: string;
  context_length: number;
  gpu_layers: number;
  reason: string;
}

export interface WSEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}
