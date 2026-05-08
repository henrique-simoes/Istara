import type { AgentCapability, AgentRole } from "@/lib/types";

export const ROLE_LABELS: Record<AgentRole, string> = {
  task_executor: "Task Executor",
  devops_audit: "DevOps Audit",
  ui_audit: "UI Audit",
  ux_evaluation: "UX Evaluation",
  user_simulation: "User Simulation",
  design_lead: "Design Lead",
  custom: "Custom",
};

export const ROLE_COLORS: Record<AgentRole, string> = {
  task_executor: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  devops_audit: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  ui_audit: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  ux_evaluation: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400",
  user_simulation: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400",
  design_lead: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
  custom: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
};

export const ALL_CAPABILITIES: { id: AgentCapability; label: string; description: string }[] = [
  { id: "chat", label: "Chat", description: "Participate in conversations" },
  { id: "skill_execution", label: "Run Skills", description: "Execute UX research skills" },
  { id: "task_creation", label: "Create Tasks", description: "Add tasks to Kanban board" },
  { id: "findings_write", label: "Write Findings", description: "Create nuggets, facts, insights" },
  { id: "rag_retrieval", label: "RAG Search", description: "Search uploaded documents" },
  { id: "a2a_messaging", label: "A2A Messaging", description: "Communicate with other agents" },
  { id: "file_upload", label: "File Upload", description: "Upload and process files" },
  { id: "web_search", label: "Web Search", description: "Search the web for information" },
];

export const STATE_COLORS: Record<string, string> = {
  idle: "text-slate-500",
  working: "text-blue-500",
  paused: "text-yellow-500",
  error: "text-red-500",
  stopped: "text-slate-400",
};
