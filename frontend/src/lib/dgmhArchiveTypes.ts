/** DGM-H Archive API types. */

export type DGMHArchiveStatus =
  | "candidate"
  | "approved"
  | "active"
  | "confirmed"
  | "archived"
  | "failed"
  | "reverted"
  | "quarantined";

export interface DGMHArchiveVariant {
  id: string;
  parent_id: string;
  root_id: string;
  generation: number;
  source_system: string;
  source_id: string;
  project_id: string;
  agent_id: string;
  governance_proposal_id: string;
  target_system: string;
  mutation_kind: string;
  mutation_surface: string;
  artifact_kind: string;
  artifact_ref: string;
  title: string;
  summary: string;
  status: DGMHArchiveStatus | string;
  lineage: string[];
  mutation: Record<string, any>;
  rollback_plan: Record<string, any>;
  evidence: any[];
  metrics_before: Record<string, any>;
  metrics_after: Record<string, any>;
  evaluation: any[];
  reasoning_memory_ids: string[];
  score: number | null;
  confidence: number;
  ucb_score: number | null;
  created_at: string | null;
  updated_at: string | null;
  evaluated_at: string | null;
  applied_at: string | null;
  reverted_at: string | null;
  confirmed_at: string | null;
}

export interface DGMHVariantCreateRequest {
  source_system?: string;
  source_id?: string;
  project_id?: string;
  agent_id?: string;
  governance_proposal_id?: string;
  parent_id?: string;
  target_system?: string;
  mutation_kind?: string;
  mutation_surface?: string;
  artifact_kind?: string;
  artifact_ref?: string;
  title: string;
  summary?: string;
  mutation?: Record<string, any>;
  rollback_plan?: Record<string, any>;
  evidence?: any[];
  metrics_before?: Record<string, any>;
  metrics_after?: Record<string, any>;
  reasoning_memory_ids?: string[];
  score?: number | null;
  confidence?: number;
  status?: string;
}

export interface DGMHVariantEvaluationRequest {
  metrics_before?: Record<string, any>;
  metrics_after?: Record<string, any>;
  passed?: boolean | null;
  evidence?: Record<string, any>;
  score?: number | null;
  confidence?: number | null;
}

export interface DGMHVariantStatusRequest {
  reason?: string;
}

export interface DGMHVariantApplyRequest {
  evidence?: Record<string, any>;
}

export interface DGMHArchiveSummary {
  total: number;
  by_status: Record<string, number>;
  by_source_system: Record<string, number>;
  by_surface: Record<string, number>;
  by_artifact_kind: Record<string, number>;
  candidate: number;
  active: number;
  confirmed: number;
  reverted: number;
  quarantined: number;
}
