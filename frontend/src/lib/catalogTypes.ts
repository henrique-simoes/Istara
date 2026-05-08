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
  codebook_version_id?: string | null;
  code_id: string;
  source_document_id?: string | null;
  source_text: string;
  source_location: string;
  coder_id: string;
  coder_type: "llm" | "human" | "llm_reviewed";
  confidence: number;
  reasoning: string;
  review_status: "pending" | "approved" | "rejected" | "modified";
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
}
