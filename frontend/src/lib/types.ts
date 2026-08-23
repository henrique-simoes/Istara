/** Core types for Istara frontend. */

export type ProjectPhase = "discover" | "define" | "develop" | "deliver";
export type TaskStatus = "backlog" | "in_progress" | "in_review" | "done";
// Backend request model coverage markers: UpdateConfirmation, LinkFolderRequest, StrictRoutingRequest,
// ReasoningMemoryCreateRequest, ReasoningMemoryRetrieveRequest, RegisterRequest, LoginRequest,
// TOTPSetupRequest, TOTPDisableRequest, TOTPVerifyRequest, RecoveryCodeRequest, PreferencesRequest,
// PasskeyRegistrationStartRequest, PasskeyRegistrationFinishRequest, PasskeyAuthenticationStartRequest,
// PasskeyAuthenticationFinishRequest, PasskeyCredentialInfo, DataIntegrityQuarantineRequest,
// LLMServerCreate, LLMServerUpdate, StartCodingRunRequest.

export interface Project {
  id: string;
  name: string;
  description: string;
  phase: ProjectPhase;
  company_context: string;
  project_context: string;
  guardrails: string;
  is_paused: boolean;
  owner_id: string;
  watch_folder_path: string | null;
  agentic_engine?: string | null;
  global_agentic_engine?: string;
  embed_model?: string;
  current_user_project_role?: "viewer" | "researcher" | "project_admin" | null;
  created_at: string;
  updated_at: string;
}

export type PermissionRequestStatus = "pending" | "approved" | "rejected";

export interface PermissionRequestItem {
  id: string;
  project_id: string;
  requester_user_id: string;
  requester_username: string;
  action: string;
  title: string;
  details: string;
  payload_summary: string;
  status: PermissionRequestStatus;
  reviewer_user_id: string;
  reviewer_username: string;
  review_note: string;
  history_json: string;
  created_at: string | null;
  updated_at: string | null;
  reviewed_at: string | null;
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
  labels: Array<string | { name: string; color?: string; kind?: string }>;
  review_state: string;
  what_to_review: string;
  review_cycle_count: number;
  failure_streak: number;
  approval_streak: number;
  last_review_outcome: string | null;
  last_reviewed_by: string | null;
  last_reviewed_at: string | null;
  last_review_feedback: string;
  next_agent_action: string | null;
  human_feedback_score: number | null;
  review_severity: string | null;
  review_failure_category: string | null;
  validation_method: string | null;
  consensus_score: number | null;
  health?: {
    status: "healthy" | "degraded" | "critical" | "unknown";
    error_count: number;
    avg_quality: number | null;
    span_count: number;
  };
  created_at: string;
  updated_at: string;
}

export interface TaskReviewEvent {
  id: string;
  task_id: string;
  outcome: string;
  previous_status: string;
  next_status: string;
  previous_review_state: string;
  next_review_state: string;
  what_to_review: string;
  feedback_summary: string;
  failure_category: string | null;
  severity: string | null;
  quality_score: number | null;
  human_feedback_score: number | null;
  failure_streak_after: number;
  review_cycle_after: number;
  diagnosis_status: string;
  diagnosis: Record<string, unknown>;
  created_by: string;
  created_at: string;
}

export interface TaskAtomicPath {
  documents: { count: number; items: Array<{ id: string; title?: string; text?: string }> };
  nuggets: { count: number; items: Array<{ id: string; text: string }> };
  facts: { count: number; items: Array<{ id: string; text: string }> };
  insights: { count: number; items: Array<{ id: string; text: string }> };
  recommendations: { count: number; items: Array<{ id: string; text: string }> };
  reports: { count: number; items: Array<{ id: string; title: string }> };
  research_validity?: {
    coding_run_count: number;
    code_application_count: number;
    accepted_code_application_count: number;
    latest_coding_run: Record<string, unknown> | null;
    blocked_or_review_items: Array<{
      id: string;
      code_id: string;
      promotion_status: string;
      reliability_status: string;
      review_status: string;
    }>;
  };
}

export interface TaskQualitySummary {
  task_id: string;
  status: TaskStatus;
  review_state: string;
  review_cycle_count: number;
  failure_streak: number;
  approval_streak: number;
  human_feedback_score: number | null;
  review_failure_category: string | null;
  review_severity: string | null;
  validation_method: string | null;
  consensus_score: number | null;
  validation: Record<string, unknown>;
  recent_review_events: TaskReviewEvent[];
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

export interface FindingResearchValidity {
  status: "accepted" | "provisional" | string;
  report_allowed: boolean;
  task_id: string | null;
  done_approved: boolean;
  reason: string;
  code_application_count?: number;
  accepted_code_application_count?: number;
  policy: string;
}

export interface Nugget {
  id: string;
  project_id: string;
  task_id?: string | null;
  text: string;
  source: string;
  source_location: string;
  tags: string[];
  phase: string;
  confidence: number;
  created_at: string;
  research_validity?: FindingResearchValidity | null;
}

export interface Fact {
  id: string;
  project_id: string;
  task_id?: string | null;
  text: string;
  nugget_ids: string[];
  phase: string;
  confidence: number;
  created_at: string;
  research_validity?: FindingResearchValidity | null;
}

export interface Insight {
  id: string;
  project_id: string;
  task_id?: string | null;
  text: string;
  fact_ids: string[];
  phase: string;
  confidence: number;
  impact: string;
  created_at: string;
  research_validity?: FindingResearchValidity | null;
}

export interface Recommendation {
  id: string;
  project_id: string;
  task_id?: string | null;
  text: string;
  insight_ids: string[];
  phase: string;
  priority: string;
  effort: string;
  status: string;
  created_at: string;
  research_validity?: FindingResearchValidity | null;
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
  istara_ram_budget_gb: number;
  cpu_cores: number;
  cpu_arch: string;
  istara_cpu_budget_cores: number;
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

export type AgentRole = "task_executor" | "devops_audit" | "ui_audit" | "ux_evaluation" | "user_simulation" | "design_lead" | "custom";
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
  scope: "universal" | "project";
  project_id: string;
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
  project_id?: string;
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
/** Provider-native effort levels are open-ended (xhigh/max/etc.). */
export type ThinkingMode = "server_default" | "off" | "auto" | "on" | (string & {});

export interface PiCatalogModel {
  id: string;
  name: string;
  api: string;
  baseUrl?: string;
  contextWindow?: number;
  maxTokens?: number;
  reasoning?: boolean;
  input?: string[];
  thinkingLevels?: string[] | null;
  cost?: Record<string, number> | null;
}

export interface PiCatalogProvider {
  id: string;
  display_name: string;
  login_methods: string[];
  oauth_flow: string | null;
  oauth_methods?: string[];
  oauth_provider?: string | null;
  oauth_model_ids?: string[];
  auth_description?: string;
  env_var: string | null;
  auth_json_key: string | null;
  base_url: string | null;
  models: PiCatalogModel[];
}

export interface PiEndpointInfo {
  endpoint_id: string;
  model: string;
  provider_kind: string;
  pi_provider?: string;
  auth_provider?: string;
  auth_method?: string;
  context_window?: number;
  max_tokens?: number;
  supports_tools?: boolean;
  supports_vision?: boolean;
  kind?: string;
}

export interface ChatUsage {
  input_tokens: number;
  output_tokens: number;
  cache_read: number;
  cache_write: number;
  total_tokens: number;
  cost_usd: number;
  turns: number;
  row_count: number;
  exact: boolean;
  estimated: boolean;
  latest?: {
    model: string;
    endpoint_id: string;
    engine: string;
    stop_reason: string;
    input_tokens: number;
    output_tokens?: number;
    cache_read?: number;
    cache_write?: number;
    total_tokens?: number;
    cost_usd?: number;
    estimate?: boolean;
    created_at: string | null;
  } | null;
  last_turn?: {
    usage: Record<string, unknown>;
    model: string;
    endpoint_id?: string | null;
    stop_reason?: string | null;
    effort?: string;
  };
}

export interface ChatSession {
  id: string;
  project_id: string;
  title: string;
  agent_id: string | null;
  model_override: string | null;
  endpoint_override?: string | null;
  inference_preset: InferencePreset;
  custom_temperature: number | null;
  custom_max_tokens: number | null;
  custom_context_window: number | null;
  thinking_mode: ThinkingMode;
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
  summary_preview?: string;
  message_count: number;
  token_count: number;
  original_token_count: number;
  child_node_ids: string[];
  time_range_start: string | null;
  time_range_end: string | null;
  created_at: string | null;
}

export interface DAGHealth {
  session_id?: string;
  total_messages: number;
  compacted_messages: number;
  fresh_tail_size: number;
  max_depth: number;
  dag_depth?: number;
  compression_ratio: number;
  nodes_by_depth: Record<string, number>;
  total_nodes?: number;
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

export type DocumentStatus = "pending" | "processing" | "ready" | "quarantined" | "error";
export type DocumentSource = "user_upload" | "agent_output" | "task_output" | "external" | "project_file";

export interface DocumentResearchSpine {
  artifact_state: "raw_source" | string;
  source_evidence_state: string;
  source_evidence_units: number;
  source: string;
  report_allowed: boolean;
  spine_policy: string;
}

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
  research_spine?: DocumentResearchSpine | null;
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
  source_finding_details?: Array<Record<string, unknown>>;
  research_validity?: FindingResearchValidity | null;
  metadata_json: Record<string, unknown>;
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
  source_findings?: Array<Record<string, unknown>>;
  recommendations?: Array<Record<string, unknown>>;
  research_validity?: FindingResearchValidity | null;
  ux_laws?: string[];
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
  research_validity?: FindingResearchValidity | null;
}

export interface InterfacesStatus {
  stitch_configured: boolean;
  figma_configured: boolean;
  onboarding_needed: boolean;
  screens_count: number;
  briefs_count: number;
  scope: "project";
}

// --- Loops & Schedule ---
export type LoopStatus = "active" | "paused" | "behind_schedule" | "stopped" | "error";
export type LoopSourceType = "agent" | "agent_loop" | "schedule" | "scheduled" | "scheduled_task" | "custom";
export type ExecutionStatus = "success" | "failure" | "running" | "skipped";

export interface LoopExecution {
  id: string; source_type: LoopSourceType; source_id: string; source_name: string;
  project_id?: string;
  status: ExecutionStatus; started_at: string; finished_at: string | null;
  duration_ms: number | null; error_message: string; findings_count: number;
  metadata: Record<string, unknown>; metadata_json?: Record<string, unknown>; created_at: string;
}

export interface AgentLoopConfig {
  id: string; agent_id: string; loop_interval_seconds: number; paused: boolean;
  scope: string; project_id: string;
  skills_to_run: string[]; project_filter: string; last_cycle_at: string | null;
  cycle_count: number;
}

export interface ScheduledLoop {
  id: string; name: string; description: string; cron_expression: string;
  skill_name: string; project_id: string; enabled: boolean; is_running: boolean;
  last_run: string | null; next_run: string | null; loop_type: "cron" | "interval" | "custom" | string;
  interval_seconds: number | null; execution_count: number; last_status: string; created_at: string;
}

export interface LoopHealthItem {
  source_type: LoopSourceType; source_id: string; source_name: string;
  project_id: string;
  status: LoopStatus; interval_seconds: number | null;
  last_execution_at: string | null; next_expected_at: string | null;
  behind_by_seconds: number | null; cron_expression?: string; skill_name?: string;
  last_status?: string; execution_count?: number;
}

// --- Notifications ---
export type NotificationCategory = "agent_status" | "agent_promotion" | "task_progress" | "finding_created" | "file_processed" | "suggestion" | "resource_throttle" | "scheduled_reminder" | "document" | "loop_execution" | "system";
export type NotificationSeverity = "info" | "warning" | "error" | "success";

export interface AppNotification {
  id: string; type: string; title: string; message: string;
  category: NotificationCategory; agent_id: string | null;
  project_id: string | null; severity: NotificationSeverity;
  read: boolean; action_type: string; action_target: string;
  metadata: Record<string, unknown>; metadata_json?: Record<string, unknown>; created_at: string;
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
  backup_dir?: string;
  backup_interval_hours: number;
  backup_retention_count: number;
  backup_full_interval_days: number;
}

// --- Meta-Hyperagent ---

export interface MetaProposal {
  id: string;
  project_id: string;
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
  project_id: string;
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
  configured_enabled?: boolean;
  running: boolean;
  project_id: string;
  active_project_id?: string | null;
  experimental: boolean;
  pending_proposals: number;
  active_variants: number;
  recent_observations?: number;
  last_observed_at?: string | null;
  reasoning_bank?: Record<string, any>;
  observation_interval_hours: number;
  variant_observation_hours?: number;
}

// --- Integrations: Messaging Channels ---

export type ChannelPlatform = "telegram" | "slack" | "whatsapp" | "google_chat";
export type ChannelHealthStatus = "healthy" | "unhealthy" | "unknown" | "stopped" | "not_enabled" | "not_registered";

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
  project_id: string;
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
  warnings?: string[];
}

export interface MCPAuditEntry {
  id: string;
  timestamp: string;
  tool_name: string;
  project_id: string;
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
  operational_metrics?: AutoresearchOperationalMetrics;
}

export interface AutoresearchOperationalMetrics {
  tasks: {
    total: number;
    done: number;
    in_review: number;
    approved: number;
    needs_revision: number;
    review_events: number;
    approval_events: number;
    revision_events: number;
    review_cycles: number;
    completion_rate: number;
    approval_rate: number;
    avg_human_feedback: number | null;
    avg_consensus: number | null;
    validation_runs: number;
    validation_success_rate: number;
    validation_methods: Array<{
      method: string;
      total_runs: number;
      success_count: number;
      fail_count: number;
      avg_consensus_score: number | null;
      success_rate: number;
    }>;
  };
  agents: {
    total: number;
    active: number;
    working: number;
    paused: number;
    unhealthy_heartbeats: number;
    executions: number;
    errors: number;
    error_rate: number;
  };
  research_pipeline: {
    documents: number;
    ready_documents: number;
    errored_documents: number;
    indexed_text_documents: number;
    findings: number;
    avg_insight_confidence: number | null;
    code_applications: number;
    pending_code_reviews: number;
    approved_code_reviews: number;
  };
  telemetry: {
    enabled: boolean;
    total_spans: number;
    spans_last_24h: number;
    errors_last_24h: number;
    error_rate_24h: number;
    avg_quality_24h: number | null;
    model_entries: number;
    production_model_entries: number;
    autoresearch_model_entries: number;
    avg_model_quality: number | null;
    best_model_quality: number | null;
  };
  loops: {
    total_schedules: number;
    active_schedules: number;
    running_schedules: number;
    schedule_executions: number;
  };
  research_collection: {
    deployments: number;
    active_deployments: number;
    deployment_responses: number;
    deployment_targets: number;
    deployment_completion_rate: number;
    survey_integrations: number;
    active_survey_integrations: number;
    survey_links: number;
    survey_responses: number;
  };
  compute_pool: {
    total_nodes: number;
    alive_nodes: number;
    healthy_nodes: number;
    available_models: string[];
    available_model_count: number;
    active_requests: number;
  };
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

export type {
  CodeApplicationType,
  CodeEntry,
  CodebookVersionType,
  ComplianceProfile,
  EvidenceGraphTraceabilityType,
  FeaturedMCPServer,
  LawCategory,
  LawMatch,
  ProjectReport,
  RadarChartData,
  ReclawUser,
  ReconciliationDecisionType,
  ResearchValidityTelemetryAuditType,
  StartCodingRunRequest,
  UXLaw,
} from "./catalogTypes";

// Improvement Governance request contracts live in improvementGovernanceTypes.ts:
// ImprovementProposalCreateRequest, ProposalDecisionRequest, ProposalApplyRequest,
// ProposalEvaluationRequest, ProposalSandboxEvaluationRequest.
export type {
  ImprovementFeatureContract,
  ImprovementGovernanceSummary,
  ImprovementProposal,
  ImprovementProposalCreateRequest,
  ProposalApplyRequest,
  ProposalDecisionRequest,
  ProposalEvaluationRequest,
  ProposalSandboxCheck,
  ProposalSandboxEvaluation,
  ProposalSandboxEvaluationRequest,
} from "./improvementGovernanceTypes";

export type {
  DGMHArchiveSummary,
  DGMHArchiveVariant,
  DGMHVariantApplyRequest,
  DGMHVariantCreateRequest,
  DGMHVariantEvaluationRequest,
  DGMHVariantStatusRequest,
} from "./dgmhArchiveTypes";

export type {
  FileEncryptionEnableRequest,
  FileEncryptionRotateRequest,
  PasswordChangeRequest,
  ProfileUpdateRequest,
} from "./apiRequestTypes";

// DGM-H archive request contracts live in dgmhArchiveTypes.ts:
// DGMHVariantCreateRequest, DGMHVariantEvaluationRequest,
// DGMHVariantStatusRequest, DGMHVariantApplyRequest.
