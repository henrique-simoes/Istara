/** ReasoningBank API types. */

export interface ReasoningMemoryItem {
  id: string;
  project_id: string;
  agent_id: string;
  source_kind: string;
  source_id: string;
  outcome: string;
  title: string;
  description: string;
  content: string;
  tags: string[];
  domain: string;
  evidence_refs: Array<Record<string, any> | string>;
  judge_score: number | null;
  confidence: number;
  status: string;
  usage_count: number;
  retrieval_score?: number;
  created_at: string | null;
  updated_at: string | null;
  expires_at: string | null;
}

export interface ReasoningBankSummary {
  total: number;
  source_kinds: Record<string, number>;
  outcomes: Record<string, number>;
  recent_24h: number;
  recent_failures_24h: number;
  recent_successes_24h: number;
}
