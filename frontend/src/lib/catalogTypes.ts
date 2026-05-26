export type LawCategory = "perception" | "cognitive" | "behavioral" | "principles";

export interface UXLaw {
  id: string;
  name: string;
  category: LawCategory;
  cluster: string;
  description: string;
  origin: { author: string; year: number; publication: string };
  key_takeaways: string[];
  related_nielsen_heuristics: string[];
  measurement_methods: string[];
  design_implications: string[];
  severity_indicators: Record<string, string>;
  examples: string[];
  academic_references: string[];
  detection_keywords: string[];
}

export interface LawMatch {
  law_id: string;
  score: number;
  law: UXLaw;
}

export interface ComplianceProfile {
  overall_score: number;
  by_category: Record<string, { score: number; laws_evaluated: number; violations: number }>;
  by_law: Array<{
    law_id: string;
    law_name: string;
    category: string;
    score: number;
    violation_count: number;
    finding_ids: string[];
  }>;
  evaluated?: boolean;
  evidence_count?: number;
  total_findings?: number;
  law_tag_count?: number;
}

export interface FeaturedMCPServer {
  id: string;
  name: string;
  description: string;
  package: string;
  repository: string;
  license: string;
  transport: string;
  tool_count: number;
  resource_count: number;
  categories: string[];
  env_vars: Array<{ name: string; description: string; required: boolean; default?: string }>;
  features: Array<{ name: string; description: string }>;
  ux_research_applications: string[];
}

export interface RadarChartData {
  categories: string[];
  category_scores: number[];
  detailed_axes: Array<{ axis: string; value: number }>;
}

export interface ReclawUser {
  id: string;
  username: string;
  email: string;
  role: "admin" | "researcher" | "viewer";
  display_name: string;
  created_at: string;
  recovery_codes?: string[];
}

export interface ProjectReport {
  id: string;
  project_id: string;
  title: string;
  layer: number;
  report_type: "study_analysis" | "synthesis" | "final_report";
  scope: string;
  executive_summary: string;
  status: "draft" | "in_progress" | "review" | "final";
  version: number;
  finding_count: number;
  mece_categories: Array<{ name: string; description: string; finding_ids: string[] }>;
  created_at: string;
  updated_at: string;
}

export interface CodebookVersionType {
  id: string;
  project_id: string;
  version: string;
  codes: CodeEntry[];
  change_log: string;
  created_by: string;
  methodology: "reflexive_ta" | "codebook_ta" | "grounded_theory";
  created_at: string | null;
}

export interface CodeEntry {
  code_id: string;
  label: string;
  brief_definition: string;
  full_definition: string;
  exclusion_criteria: string;
  typical_example: string;
  boundary_example?: string;
  coding_method: string;
  frequency: number;
  parent_theme?: string | null;
}

export interface CodeApplicationType {
  id: string;
  project_id: string;
  task_id?: string | null;
  codebook_version_id?: string | null;
  code_id: string;
  evidence_unit_id?: string | null;
  coding_run_id?: string | null;
  source_document_id?: string | null;
  source_text: string;
  source_location: string;
  start_offset?: number | null;
  end_offset?: number | null;
  coder_id: string;
  coder_type: "llm" | "human" | "llm_reviewed";
  model_name?: string;
  donor_id?: string;
  route_id?: string;
  route_evidence?: Record<string, unknown>;
  confidence: number;
  reasoning: string;
  reliability_status?: "unknown" | "accepted" | "reliable" | "passed" | "needs_reconciliation" | "needs_human_review" | "blocked" | string;
  reconciliation_status?: "unreconciled" | "accepted" | "reconciled" | "rejected" | string;
  promotion_status?: "blocked" | "accepted" | "needs_reconciliation" | "needs_human_review" | string;
  review_status: "pending" | "approved" | "rejected" | "modified";
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
}

export interface ReconciliationDecisionType {
  id: string;
  project_id: string;
  task_id?: string | null;
  coding_run_id?: string | null;
  evidence_unit_id?: string | null;
  code_application_id?: string | null;
  decision_type: "accepted" | "rejected" | "revised" | "needs_human_review" | string;
  source: string;
  accepted_code_id?: string;
  rationale: string;
  decided_by: string;
  previous_state?: Record<string, unknown>;
  resolved_state?: Record<string, unknown>;
  route_evidence?: Record<string, unknown>;
  created_at: string;
}

export interface EvidenceGraphTraceabilityType {
  project_id: string;
  filters: {
    report_id?: string | null;
    task_id?: string | null;
    finding_id?: string | null;
    limit: number;
  };
  retrieval_mode: "graph+hybrid" | string;
  contract: Record<string, string>;
  reports: ProjectReport[];
  findings: Array<Record<string, unknown>>;
  task_dependencies: Array<{
    task_id: string;
    report_gate: Record<string, unknown>;
    code_application_count: number;
    unresolved_code_application_count: number;
    accepted_code_application_count: number;
  }>;
  report_dependencies: Array<{
    report_id: string;
    title: string;
    layer: number;
    finding_ids: string[];
    task_ids: string[];
    finding_count: number;
    low_agreement_dependency_count: number;
    report_allowed_by_research_validity: boolean;
    blocked_code_applications: CodeApplicationType[];
  }>;
  coding_runs: Array<Record<string, unknown>>;
  code_applications: CodeApplicationType[];
  reconciliation_decisions: ReconciliationDecisionType[];
  evidence_graph_edges: Array<Record<string, unknown>>;
  low_agreement_dependencies: CodeApplicationType[];
  summary: Record<string, number>;
}

export interface ResearchValidityTelemetryAuditType {
  project_id: string;
  status: "ok" | "unavailable" | string;
  span_count?: number;
  operation_counts: Record<string, number>;
  category_counts: Record<string, number>;
  status_counts?: Record<string, number>;
  retrieval_mode_counts: Record<string, number>;
  donor_lifecycle_counts: Record<string, number>;
  route_evidence_count: number;
  route_evidence?: Array<{
    operation: string;
    status: string;
    model_name: string;
    route_id: string;
    donor_id: string;
    coding_run_id: string;
    evidence_unit_id: string;
    retrieval_mode: string;
    reliability_score?: number | null;
    created_at?: string | null;
  }>;
  coding_run_ids: string[];
  evidence_unit_ids: string[];
  codebook_version_ids: string[];
  reliability_summary?: {
    count: number;
    min: number | null;
    max: number | null;
    avg: number | null;
  };
  unobserved_contract_operations: string[];
  content_policy: string;
  protected_fields?: string[];
}

export interface StartCodingRunRequest {
  task_id?: string | null;
  evidence_unit_ids?: string[] | null;
  codebook_version_id?: string | null;
  threshold?: number;
  max_coders?: number;
  limit?: number;
}
