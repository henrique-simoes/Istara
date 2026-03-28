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
  agent_id: string | null;
  title: string;
  description: string;
  status: TaskStatus;
  skill_name: string;
  agent_notes: string;
  user_context: string;
  progress: number;
  position: number;
  priority: string;
  input_document_ids: string[];
  output_document_ids: string[];
  urls: string[];
  instructions: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  sources?: { source: string; score: number; page?: number }[];
  agent_id?: string;
  agent_name?: string;
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

export type AgentRole = "task_executor" | "devops_audit" | "ui_audit" | "ux_evaluation" | "user_simulation" | "custom";
export type AgentState = "idle" | "working" | "paused" | "error" | "stopped";
export type HeartbeatStatus = "healthy" | "degraded" | "error" | "stopped";
export type AgentCapability = "web_search" | "file_upload" | "skill_execution" | "task_creation" | "findings_write" | "chat" | "rag_retrieval" | "a2a_messaging";

export interface Agent {
  id: string;
  name: string;
  avatar_path: string | null;
  role: AgentRole;
  system_prompt: string;
  capabilities: AgentCapability[];
  memory: Record<string, unknown>;
  heartbeat_interval_seconds: number;
  heartbeat_status: HeartbeatStatus;
  last_heartbeat_at: string | null;
  state: AgentState;
  current_task: string;
  error_count: number;
  executions: number;
  is_system: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface A2AMessage {
  id: string;
  from_agent_id: string;
  to_agent_id: string | null;
  message_type: string;
  content: string;
  metadata: Record<string, unknown>;
  read: boolean;
  created_at: string;
}

export interface AgentCapacityCheck {
  can_create: boolean;
  reason: string;
  current_agents: number;
  max_agents: number;
  ram_available_gb: number;
  ram_total_gb: number;
  cpu_cores: number;
  pressure: string;
}

export type InferencePreset = "lightweight" | "medium" | "high" | "custom";

export interface ChatSession {
  id: string;
  project_id: string;
  title: string;
  agent_id: string | null;
  model_override: string | null;
  inference_preset: InferencePreset;
  custom_temperature: number | null;
  custom_max_tokens: number | null;
  custom_context_window: number | null;
  starred: boolean;
  archived: boolean;
  message_count: number;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface InferencePresetConfig {
  label: string;
  description: string;
  temperature: number | null;
  max_tokens: number | null;
  context_window: number | null;
}

export interface WSEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

// --- Context DAG ---

export interface DAGNode {
  id: string;
  parent_id: string | null;
  depth: number;
  summary_text: string;
  message_count: number;
  token_count: number;
  original_token_count: number;
  child_node_ids: string[];
  time_range_start: string;
  time_range_end: string;
  created_at: string;
}

export interface DAGHealth {
  total_messages: number;
  compacted_messages: number;
  fresh_tail_size: number;
  max_depth: number;
  compression_ratio: number;
  nodes_by_depth: Record<number, number>;
  dag_enabled: boolean;
}

export interface DAGExpandResult {
  node_id: string;
  depth: number;
  items: Array<{
    id: string;
    role?: string;
    content: string;
    created_at?: string;
    type: "message" | "summary";
  }>;
}

export interface DAGGrepResult {
  query: string;
  results: Array<{
    message_id: string;
    role: string;
    content_excerpt: string;
    created_at: string;
    dag_node_id: string | null;
  }>;
}

// --- Documents ---

export type DocumentStatus = "pending" | "processing" | "ready" | "error";
export type DocumentSource = "user_upload" | "agent_output" | "task_output" | "external" | "project_file";

export interface ReclawDocument {
  id: string;
  project_id: string;
  title: string;
  description: string;
  file_path: string;
  file_name: string;
  file_type: string;
  file_size: number;
  status: DocumentStatus;
  source: DocumentSource;
  task_id: string | null;
  agent_ids: string[];
  skill_names: string[];
  tags: string[];
  phase: string;
  atomic_path: Record<string, unknown>;
  content_preview: string;
  content_text?: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentContent {
  id: string;
  file_name: string;
  type: string;
  content: string | null;
  media_url?: string;
  pages?: number;
  size: number;
}

export interface DocumentTag {
  name: string;
  count: number;
}

export interface DocumentStats {
  total: number;
  by_source: Record<string, number>;
  by_phase: Record<string, number>;
  by_status: Record<string, number>;
}

// --- Interfaces / Design ---

export type DesignScreenStatus = "generating" | "ready" | "error";
export type DeviceType = "MOBILE" | "DESKTOP" | "TABLET" | "AGNOSTIC";

export interface DesignScreen {
  id: string;
  project_id: string;
  title: string;
  description: string;
  prompt: string;
  device_type: DeviceType;
  model_used: string;
  html_content: string;
  screenshot_path: string;
  stitch_project_id: string | null;
  stitch_screen_id: string | null;
  parent_screen_id: string | null;
  variant_type: string | null;
  figma_file_key: string | null;
  figma_node_id: string | null;
  status: DesignScreenStatus;
  source_findings: string[];
  metadata_json: string;
  created_at: string;
  updated_at: string;
}

export interface DesignBrief {
  id: string;
  project_id: string;
  title: string;
  content: string;
  source_insight_ids: string[];
  source_recommendation_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface DesignDecision {
  id: string;
  project_id: string;
  agent_id: string | null;
  text: string;
  recommendation_ids: string[];
  screen_ids: string[];
  rationale: string;
  phase: string;
  confidence: number;
  created_at: string;
}

export interface InterfacesStatus {
  stitch_configured: boolean;
  figma_configured: boolean;
  onboarding_needed: boolean;
  screens_count: number;
  briefs_count: number;
}

// --- Loops & Schedule ---
export type LoopStatus = "active" | "paused" | "behind_schedule" | "stopped" | "error";
export type ExecutionStatus = "success" | "failure" | "running" | "skipped";

export interface LoopExecution {
  id: string; source_type: string; source_id: string; source_name: string;
  status: ExecutionStatus; started_at: string; finished_at: string | null;
  duration_ms: number | null; error_message: string; findings_count: number;
  metadata: Record<string, unknown>; created_at: string;
}

export interface AgentLoopConfig {
  id: string; agent_id: string; loop_interval_seconds: number; paused: boolean;
  skills_to_run: string[]; project_filter: string; last_cycle_at: string | null;
  cycle_count: number;
}

export interface LoopHealthItem {
  source_type: string; source_id: string; source_name: string;
  status: LoopStatus; interval_seconds: number;
  last_execution_at: string | null; next_expected_at: string | null;
  behind_by_seconds: number;
}

// --- Notifications ---
export type NotificationCategory = "agent_status" | "task_progress" | "finding_created" | "file_processed" | "suggestion" | "resource_throttle" | "scheduled_reminder" | "document" | "loop_execution" | "system";
export type NotificationSeverity = "info" | "warning" | "error" | "success";

export interface AppNotification {
  id: string; type: string; title: string; message: string;
  category: NotificationCategory; agent_id: string | null;
  project_id: string | null; severity: NotificationSeverity;
  read: boolean; action_type: string; action_target: string;
  metadata: Record<string, unknown>; created_at: string;
}

export interface NotificationPreference {
  id: string; category: string; agent_id: string | null;
  show_toast: boolean; show_center: boolean; email_forward: boolean;
}

// --- Backup System ---

export interface BackupRecord {
  id: string;
  filename: string;
  backup_type: "full" | "incremental";
  parent_id: string | null;
  size_bytes: number;
  file_count: number;
  status: "completed" | "failed" | "in_progress" | "verified";
  error_message: string;
  components: Record<string, any>;
  checksum: string;
  created_at: string;
  verified_at: string | null;
}

export interface BackupConfig {
  backup_enabled: boolean;
  backup_interval_hours: number;
  backup_retention_count: number;
  backup_full_interval_days: number;
}

// --- Meta-Hyperagent ---

export interface MetaProposal {
  id: string;
  target_system: string;
  parameter_path: string;
  current_value: any;
  proposed_value: any;
  reason: string;
  evidence: Record<string, any>[];
  confidence: number;
  expected_impact: string;
  status: string;
  variant_id: string | null;
  created_at: string;
  reviewed_at: string | null;
  applied_at: string | null;
}

export interface MetaVariant {
  id: string;
  proposal_id: string;
  target_system: string;
  parameter_path: string;
  old_value: any;
  new_value: any;
  applied_at: string;
  reverted_at: string | null;
  metrics_before: Record<string, any>;
  metrics_after: Record<string, any> | null;
  observation_window_hours: number;
  status: "active" | "reverted" | "confirmed";
}

export interface MetaHyperagentStatus {
  enabled: boolean;
  experimental: boolean;
  pending_proposals: number;
  active_variants: number;
  observation_interval_hours: number;
}

// --- Integrations: Messaging Channels ---

export type ChannelPlatform = "telegram" | "slack" | "whatsapp" | "google_chat";
export type ChannelHealthStatus = "healthy" | "unhealthy" | "unknown";

export interface ChannelInstance {
  id: string;
  platform: ChannelPlatform;
  name: string;
  project_id: string | null;
  is_active: boolean;
  health_status: ChannelHealthStatus;
  last_health_at: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChannelMessage {
  id: string;
  channel_instance_id: string;
  project_id: string | null;
  direction: "inbound" | "outbound";
  sender_id: string;
  sender_name: string;
  content: string;
  content_type: "text" | "audio" | "image" | "file";
  thread_id: string | null;
  created_at: string;
}

export interface ChannelConversation {
  id: string;
  channel_instance_id: string;
  project_id: string | null;
  participant_id: string;
  participant_name: string;
  deployment_id: string | null;
  state: "active" | "completed" | "paused" | "expired";
  current_question_index: number;
  started_at: string;
  last_message_at: string | null;
  completed_at: string | null;
}

// --- Integrations: Research Deployments ---

export interface ResearchDeployment {
  id: string;
  project_id: string;
  name: string;
  deployment_type: "interview" | "survey" | "diary_study";
  skill_name: string;
  questions: Array<{ text: string; type?: string }>;
  config: Record<string, any>;
  channel_instance_ids: string[];
  state: "draft" | "active" | "paused" | "completed";
  target_responses: number;
  current_responses: number;
  created_at: string;
  updated_at: string;
}

export interface DeploymentAnalytics {
  deployment_id: string;
  deployment_name: string;
  deployment_type: string;
  state: string;
  target_responses: number;
  current_responses: number;
  response_rate: number;
  completion_rate: number;
  active_conversations: number;
  completed_conversations: number;
  failed_conversations: number;
  total_messages: number;
  per_question_stats: Array<{
    index: number;
    text: string;
    response_count: number;
    skip_count: number;
  }>;
  most_answered_questions: Array<any>;
  least_answered_questions: Array<any>;
}

// --- Integrations: Survey Platforms ---

export interface SurveyIntegration {
  id: string;
  platform: "surveymonkey" | "google_forms" | "typeform";
  name: string;
  project_id: string | null;
  is_active: boolean;
  last_sync_at: string | null;
  created_at: string;
}

export interface SurveyLink {
  id: string;
  integration_id: string;
  project_id: string;
  external_survey_id: string;
  external_survey_name: string;
  response_count: number;
  last_response_at: string | null;
  created_at: string;
}

// --- Integrations: MCP ---

export interface MCPServerConfig {
  id: string;
  name: string;
  url: string;
  transport: "http" | "stdio" | "websocket";
  is_active: boolean;
  tools: Array<{ name: string; description: string; input_schema: any }>;
  last_discovery_at: string | null;
  health_status: string;
  created_at: string;
}

export interface MCPAccessPolicy {
  id: string;
  name: string;
  description: string;
  tools: Record<string, { allowed: boolean; risk: "low" | "sensitive" | "high" }>;
  resources: Record<string, { allowed: boolean; risk: "low" | "sensitive" | "high" }>;
  limits: {
    allowed_project_ids: string[];
    max_findings_per_request: number;
    max_skill_executions_per_hour: number;
  };
}

export interface MCPAuditEntry {
  id: string;
  timestamp: string;
  tool_name: string;
  caller_info: string;
  access_granted: boolean;
  result_summary: string;
  duration_ms: number;
}

// --- Autoresearch (Karpathy-inspired) ---

export type AutoresearchLoopType = "skill_prompt" | "model_temp" | "rag_params" | "persona" | "question_bank" | "ui_sim";

export interface AutoresearchExperiment {
  id: string;
  loop_type: AutoresearchLoopType;
  target_name: string;
  hypothesis: string;
  mutation_description: string;
  baseline_score: number;
  experiment_score: number | null;
  delta: number;
  kept: boolean;
  status: "running" | "completed" | "failed" | "reverted";
  error_message: string;
  project_id: string;
  started_at: string;
  completed_at: string | null;
}

export interface AutoresearchConfig {
  enabled: boolean;
  max_experiments_per_run: number;
  max_daily_experiments: number;
}

export interface AutoresearchStatus {
  running: boolean;
  enabled: boolean;
  current_experiment: AutoresearchExperiment | null;
}

export interface ModelSkillLeaderboard {
  skill_name: string;
  model_name: string;
  temperature: number;
  best_quality: number;
  quality_ema: number;
  executions: number;
  avg_quality: number;
}

// --- Laws of UX ---

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
}

export interface RadarChartData {
  categories: string[];
  category_scores: number[];
  detailed_axes: Array<{ axis: string; value: number }>;
}
