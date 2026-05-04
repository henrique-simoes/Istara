/** Improvement Governance API types. */

export type ImprovementProposalStatus =
  | "draft"
  | "proposed"
  | "approved"
  | "applied"
  | "rejected"
  | "reverted"
  | "failed"
  | "quarantined";

export interface ImprovementProposal {
  id: string;
  source_system: string;
  source_id: string;
  project_id: string;
  agent_id: string;
  title: string;
  summary: string;
  rationale: string;
  affected_surfaces: string[];
  risk_level: string;
  approval_policy: string;
  status: ImprovementProposalStatus | string;
  before_state: Record<string, any>;
  proposed_change: Record<string, any>;
  rollback_plan: Record<string, any>;
  evidence: any[];
  metrics_before: Record<string, any>;
  metrics_after: Record<string, any>;
  evaluation_runs: any[];
  reasoning_memory_ids: string[];
  improvement_score: number | null;
  confidence: number;
  requires_human_approval: boolean;
  auto_apply_allowed: boolean;
  created_by: string;
  approved_by: string;
  applied_by: string;
  reverted_by: string;
  created_at: string | null;
  updated_at: string | null;
  approved_at: string | null;
  applied_at: string | null;
  reverted_at: string | null;
}

export interface ImprovementProposalCreateRequest {
  source_system?: string;
  source_id?: string;
  project_id?: string;
  agent_id?: string;
  title: string;
  summary?: string;
  rationale?: string;
  affected_surfaces?: string[];
  risk_level?: string | null;
  approval_policy?: string | null;
  before_state?: Record<string, any>;
  proposed_change?: Record<string, any>;
  rollback_plan?: Record<string, any>;
  evidence?: any[];
  metrics_before?: Record<string, any>;
  metrics_after?: Record<string, any>;
  reasoning_memory_ids?: string[];
  improvement_score?: number | null;
  confidence?: number;
}

export interface ProposalDecisionRequest {
  note?: string;
  reason?: string;
}

export interface ProposalApplyRequest {
  evidence?: Record<string, any>;
}

export interface ProposalEvaluationRequest {
  metrics_before?: Record<string, any>;
  metrics_after?: Record<string, any>;
  passed?: boolean | null;
  evidence?: Record<string, any>;
}

export interface ProposalSandboxEvaluationRequest {
  evidence?: Record<string, any>;
}

export interface ProposalSandboxCheck {
  id: string;
  passed: boolean;
  severity: "blocker" | "warning" | string;
  message: string;
  detail?: any;
}

export interface ProposalSandboxEvaluation {
  event: "sandbox_evaluation" | string;
  proposal_id: string;
  source_system: string;
  risk_level: string;
  affected_surfaces: string[];
  passed: boolean;
  blockers: ProposalSandboxCheck[];
  warnings: ProposalSandboxCheck[];
  checks: ProposalSandboxCheck[];
  evaluated_at: string;
}

export interface ImprovementGovernanceSummary {
  total: number;
  by_status: Record<string, number>;
  by_source_system: Record<string, number>;
  by_surface: Record<string, number>;
  pending_human_approval: number;
  applied: number;
  reverted: number;
  quarantined: number;
}

export interface ImprovementFeatureContract {
  feature: string;
  surfaces: string[];
  required_evidence: string[];
}
