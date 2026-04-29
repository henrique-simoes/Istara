"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, FileText, Globe, GripVertical, Plus, Trash2 } from "lucide-react";
import { useTaskStore } from "@/stores/taskStore";
import { useProjectStore } from "@/stores/projectStore";
import { useAgentStore } from "@/stores/agentStore";
import type { Task, TaskStatus } from "@/lib/types";
import { cn, statusLabel } from "@/lib/utils";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import ViewOnboarding from "@/components/common/ViewOnboarding";
import TaskEditor from "./TaskEditor";

const COLUMNS: { id: TaskStatus; color: string }[] = [
  { id: "backlog", color: "border-t-slate-400" },
  { id: "in_progress", color: "border-t-blue-500" },
  { id: "in_review", color: "border-t-yellow-500" },
  { id: "done", color: "border-t-green-500" },
];

const PRIORITY_COLORS: Record<string, string> = {
  urgent: "border-l-red-500",
  high: "border-l-orange-500",
  medium: "border-l-blue-500",
  low: "border-l-slate-300 dark:border-l-slate-600",
};

const PRIORITY_LABELS: Record<string, string> = {
  urgent: "Urgent",
  high: "High",
  medium: "Medium",
  low: "Low",
};

const PRIORITY_DOT_COLORS: Record<string, string> = {
  urgent: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-blue-500",
  low: "bg-slate-400",
};

function AgentMiniAvatar({ agentId }: { agentId: string }) {
  const agents = useAgentStore((s) => s.agents);
  const agent = agents.find((a) => a.id === agentId);
  if (!agent) return null;
  const colors = ["bg-blue-500", "bg-green-500", "bg-purple-500", "bg-orange-500", "bg-pink-500", "bg-cyan-500"];
  const color = colors[agent.name.charCodeAt(0) % colors.length];
  return (
    <div className={cn("h-6 w-6 shrink-0 rounded-full flex items-center justify-center text-white text-[10px] font-semibold", color)} title={agent.name}>
      {agent.name.charAt(0).toUpperCase()}
    </div>
  );
}

function AgentAssignMenu({ taskId, currentAgentId, onClose }: { taskId: string; currentAgentId: string | null; onClose: () => void }) {
  const agents = useAgentStore((s) => s.agents);
  const { updateTask } = useTaskStore();
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div ref={menuRef} className="absolute right-0 top-8 z-50 w-52 rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-800">
      <button
        onClick={async (e) => {
          e.stopPropagation();
          await updateTask(taskId, { agent_id: null });
          onClose();
        }}
        className={cn("w-full px-3 py-2 text-left text-xs hover:bg-slate-50 dark:hover:bg-slate-700", !currentAgentId && "bg-slate-50 dark:bg-slate-700")}
      >
        Unassigned
      </button>
      {agents.filter((a) => a.is_active).map((agent) => (
        <button
          key={agent.id}
          onClick={async (e) => {
            e.stopPropagation();
            await updateTask(taskId, { agent_id: agent.id });
            onClose();
          }}
          className={cn("w-full px-3 py-2 text-left text-xs hover:bg-slate-50 dark:hover:bg-slate-700", currentAgentId === agent.id && "bg-istara-50 dark:bg-istara-900/20")}
        >
          <span className="truncate text-slate-700 dark:text-slate-300">{agent.name}</span>
        </button>
      ))}
    </div>
  );
}

function PriorityPicker({ taskId, currentPriority, onClose }: { taskId: string; currentPriority: string; onClose: () => void }) {
  const { updateTask } = useTaskStore();
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div ref={menuRef} className="absolute left-0 top-7 z-50 w-36 rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-800">
      {(["urgent", "high", "medium", "low"] as const).map((p) => (
        <button
          key={p}
          onClick={async (e) => {
            e.stopPropagation();
            await updateTask(taskId, { priority: p });
            onClose();
          }}
          className={cn("flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-slate-50 dark:hover:bg-slate-700", currentPriority === p && "bg-slate-50 dark:bg-slate-700")}
        >
          <span className={cn("h-2 w-2 rounded-full", PRIORITY_DOT_COLORS[p])} />
          {PRIORITY_LABELS[p]}
        </button>
      ))}
    </div>
  );
}

function TaskCard({ task, onOpen, onDelete }: { task: Task; onOpen: () => void; onDelete: () => void }) {
  const [showAgentMenu, setShowAgentMenu] = useState(false);
  const [showPriorityMenu, setShowPriorityMenu] = useState(false);
  const priority = task.priority || "medium";
  const labelNames = (task.labels || []).map((l) => (typeof l === "string" ? l : l.name)).filter(Boolean);

  return (
    <div
      draggable
      onDragStart={(e) => e.dataTransfer.setData("taskId", task.id)}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
      role="button"
      tabIndex={0}
      className={cn("rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-istara-500 dark:border-slate-700 dark:bg-slate-800 border-l-[3px]", PRIORITY_COLORS[priority])}
    >
      <div className="flex items-start gap-2">
        <GripVertical size={14} className="mt-0.5 shrink-0 text-slate-300" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className="min-w-0 flex-1 truncate text-sm font-medium text-slate-900 dark:text-white">{task.title}</p>
            <div className="relative shrink-0">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowAgentMenu((v) => !v);
                }}
                className="rounded-full hover:ring-2 hover:ring-istara-300"
                aria-label="Change assigned agent"
              >
                {task.agent_id ? <AgentMiniAvatar agentId={task.agent_id} /> : <span className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-dashed border-slate-300 text-slate-400"><Plus size={10} /></span>}
              </button>
              {showAgentMenu && <AgentAssignMenu taskId={task.id} currentAgentId={task.agent_id} onClose={() => setShowAgentMenu(false)} />}
            </div>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {task.skill_name && <span className="rounded bg-istara-100 px-1.5 py-0.5 text-[10px] text-istara-700 dark:bg-istara-900/30 dark:text-istara-300">{task.skill_name}</span>}
            {labelNames.slice(0, 3).map((name) => <span key={name} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 dark:bg-slate-700 dark:text-slate-300">{name}</span>)}
            {task.review_state && task.review_state !== "none" && (
              <span className={cn("rounded px-1.5 py-0.5 text-[10px]", task.review_state === "approved" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" : task.review_state === "awaiting_review" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300")}>
                {task.review_state.replace(/_/g, " ")}
              </span>
            )}
            {task.failure_streak > 0 && <span className="rounded bg-red-50 px-1.5 py-0.5 text-[10px] text-red-700 dark:bg-red-950/40 dark:text-red-300">{task.failure_streak}x revision</span>}
            {task.consensus_score != null && task.consensus_score > 0 && <span className="rounded bg-teal-100 px-1.5 py-0.5 text-[10px] text-teal-700 dark:bg-teal-900/30 dark:text-teal-300">{Math.round(task.consensus_score * 100)}% consensus</span>}
            {task.human_feedback_score != null && <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 dark:bg-slate-700 dark:text-slate-300">{Math.round(task.human_feedback_score * 100)}% review</span>}
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowPriorityMenu((v) => !v);
                }}
                className="inline-flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300"
                aria-label="Change priority"
              >
                <span className={cn("h-1.5 w-1.5 rounded-full", PRIORITY_DOT_COLORS[priority])} />
                {PRIORITY_LABELS[priority]}
                <ChevronDown size={8} />
              </button>
              {showPriorityMenu && <PriorityPicker taskId={task.id} currentPriority={priority} onClose={() => setShowPriorityMenu(false)} />}
            </div>
            {((task.input_document_ids?.length || 0) + (task.output_document_ids?.length || 0)) > 0 && <span className="inline-flex items-center gap-0.5 rounded bg-purple-100 px-1.5 py-0.5 text-[10px] text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"><FileText size={10} />{(task.input_document_ids?.length || 0) + (task.output_document_ids?.length || 0)}</span>}
            {(task.urls?.length || 0) > 0 && <span className="inline-flex items-center gap-0.5 rounded bg-blue-100 px-1.5 py-0.5 text-[10px] text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"><Globe size={10} />{task.urls.length}</span>}
          </div>

          {task.progress > 0 && task.progress < 1 && (
            <div className="mt-2">
              <div className="h-1.5 w-full rounded-full bg-slate-200 dark:bg-slate-700">
                <div className="h-1.5 rounded-full bg-istara-500 transition-all" style={{ width: `${task.progress * 100}%` }} />
              </div>
            </div>
          )}

          <div className="mt-2 flex items-center justify-between gap-2 text-[11px] text-slate-400">
            <span className="min-w-0 truncate">{task.description || task.agent_notes || "Open task details"}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30"
              aria-label={`Delete ${task.title}`}
              title="Delete task"
            >
              <Trash2 size={12} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function KanbanBoard() {
  const { tasks, fetchTasks, createTask, moveTask, deleteTask } = useTaskStore();
  const { activeProjectId } = useProjectStore();
  const { agents, fetchAgents } = useAgentStore();
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [addingTo, setAddingTo] = useState<TaskStatus | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [editingTask, setEditingTask] = useState<string | null>(null);

  useEffect(() => {
    if (activeProjectId) fetchTasks(activeProjectId);
  }, [activeProjectId, fetchTasks]);

  useEffect(() => {
    if (agents.length === 0) fetchAgents();
  }, [agents.length, fetchAgents]);

  const handleCreate = async (status: TaskStatus) => {
    if (!newTaskTitle.trim() || !activeProjectId) return;
    const task = await createTask(activeProjectId, newTaskTitle.trim());
    if (status !== "backlog") await moveTask(task.id, status === "done" ? "in_review" : status);
    setNewTaskTitle("");
    setAddingTo(null);
  };

  const handleDrop = async (taskId: string, newStatus: TaskStatus) => {
    try {
      await moveTask(taskId, newStatus);
    } catch (e) {
      console.error("Failed to move task:", e);
    }
  };

  if (!activeProjectId) {
    return <div className="flex flex-1 items-center justify-center text-slate-400"><p>Select a project to see tasks.</p></div>;
  }

  return (
    <div id="tour-target-kanban" className="flex-1 overflow-x-auto p-4">
      <ViewOnboarding viewId="tasks" title="Research Workflow" description="Kanban board of research tasks. Agents create tasks when you upload files. Drag to reorder, attach documents, track progress." chatPrompt="How do tasks work?" />
      <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">Tasks</h2>

      <div className="flex min-w-max gap-4">
        {COLUMNS.map((col) => {
          const columnTasks = tasks.filter((t) => t.status === col.id);
          return (
            <div
              key={col.id}
              className={cn("w-80 xl:w-96 flex-shrink-0 rounded-lg bg-slate-50 dark:bg-slate-900 border-t-4", col.color)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const taskId = e.dataTransfer.getData("taskId");
                if (taskId) handleDrop(taskId, col.id);
              }}
            >
              <div className="flex items-center justify-between p-3 pb-2">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">{statusLabel(col.id)}</h3>
                  <span className="rounded-full bg-slate-200 px-1.5 py-0.5 text-xs text-slate-500 dark:bg-slate-700">{columnTasks.length}</span>
                </div>
                <button onClick={() => setAddingTo(addingTo === col.id ? null : col.id)} aria-label={`Add task to ${statusLabel(col.id)}`} className="rounded p-1 text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800">
                  <Plus size={14} />
                </button>
              </div>

              {addingTo === col.id && (
                <div className="px-3 pb-2">
                  <input
                    type="text"
                    placeholder="Task title..."
                    value={newTaskTitle}
                    onChange={(e) => setNewTaskTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleCreate(col.id);
                      if (e.key === "Escape") setAddingTo(null);
                    }}
                    className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-istara-500 dark:border-slate-700 dark:bg-slate-800"
                    autoFocus
                  />
                </div>
              )}

              <div className="min-h-[100px] space-y-2 p-2">
                {columnTasks.map((task) => (
                  <TaskCard key={task.id} task={task} onOpen={() => setEditingTask(task.id)} onDelete={() => setDeleteConfirm(task.id)} />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {editingTask && (() => {
        const task = tasks.find((t) => t.id === editingTask);
        return task ? <TaskEditor task={task} onClose={() => { setEditingTask(null); if (activeProjectId) fetchTasks(activeProjectId); }} /> : null;
      })()}

      <ConfirmDialog
        open={!!deleteConfirm}
        title="Delete Task"
        message="Are you sure you want to delete this task? This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => {
          if (deleteConfirm) deleteTask(deleteConfirm);
          setDeleteConfirm(null);
        }}
        onCancel={() => setDeleteConfirm(null)}
      />
    </div>
  );
}
