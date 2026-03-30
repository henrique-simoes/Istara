"use client";

import { useEffect, useState, useRef } from "react";
import { Plus, GripVertical, Bot, User, Trash2, ChevronDown, FileStack, FileText, Globe } from "lucide-react";
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

  const bgColors = [
    "bg-blue-500", "bg-green-500", "bg-purple-500", "bg-orange-500",
    "bg-pink-500", "bg-cyan-500", "bg-indigo-500", "bg-teal-500",
  ];
  const colorIdx = agent.name.charCodeAt(0) % bgColors.length;

  return (
    <div
      className={cn(
        "w-6 h-6 rounded-full flex items-center justify-center text-white text-[10px] font-semibold shrink-0",
        bgColors[colorIdx]
      )}
      title={agent.name}
    >
      {agent.name.charAt(0).toUpperCase()}
    </div>
  );
}

function AgentAssignMenu({
  taskId,
  currentAgentId,
  onClose,
}: {
  taskId: string;
  currentAgentId: string | null;
  onClose: () => void;
}) {
  const agents = useAgentStore((s) => s.agents);
  const { updateTask } = useTaskStore();
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div
      ref={menuRef}
      className="absolute right-0 top-8 z-50 w-48 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1 max-h-56 overflow-y-auto"
    >
      <button
        onClick={async (e) => {
          e.stopPropagation();
          await updateTask(taskId, { agent_id: null });
          onClose();
        }}
        className={cn(
          "w-full text-left px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 flex items-center gap-2",
          !currentAgentId && "bg-slate-50 dark:bg-slate-700"
        )}
      >
        <span className="w-5 h-5 rounded-full bg-slate-200 dark:bg-slate-600 flex items-center justify-center text-[10px] text-slate-500">?</span>
        <span className="text-slate-600 dark:text-slate-300">Unassigned</span>
      </button>
      {agents.filter((a) => a.is_active).map((agent) => {
        const bgColors = [
          "bg-blue-500", "bg-green-500", "bg-purple-500", "bg-orange-500",
          "bg-pink-500", "bg-cyan-500", "bg-indigo-500", "bg-teal-500",
        ];
        const colorIdx = agent.name.charCodeAt(0) % bgColors.length;
        return (
          <button
            key={agent.id}
            onClick={async (e) => {
              e.stopPropagation();
              await updateTask(taskId, { agent_id: agent.id });
              onClose();
            }}
            className={cn(
              "w-full text-left px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 flex items-center gap-2",
              currentAgentId === agent.id && "bg-istara-50 dark:bg-istara-900/20"
            )}
          >
            <span className={cn("w-5 h-5 rounded-full flex items-center justify-center text-white text-[10px] font-semibold", bgColors[colorIdx])}>
              {agent.name.charAt(0).toUpperCase()}
            </span>
            <span className="text-slate-700 dark:text-slate-300 truncate">{agent.name}</span>
            {agent.is_system && <span className="text-[9px] text-slate-400 ml-auto">system</span>}
          </button>
        );
      })}
    </div>
  );
}

function PriorityPicker({
  taskId,
  currentPriority,
  onClose,
}: {
  taskId: string;
  currentPriority: string;
  onClose: () => void;
}) {
  const { updateTask } = useTaskStore();
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div
      ref={menuRef}
      className="absolute left-0 top-6 z-50 w-32 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1"
    >
      {(["urgent", "high", "medium", "low"] as const).map((p) => (
        <button
          key={p}
          onClick={async (e) => {
            e.stopPropagation();
            await updateTask(taskId, { priority: p });
            onClose();
          }}
          className={cn(
            "w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 flex items-center gap-2",
            currentPriority === p && "bg-slate-50 dark:bg-slate-700"
          )}
        >
          <span className={cn("w-2 h-2 rounded-full", PRIORITY_DOT_COLORS[p])} />
          <span className="text-slate-700 dark:text-slate-300">{PRIORITY_LABELS[p]}</span>
        </button>
      ))}
    </div>
  );
}

function TaskCard({
  task,
  expanded,
  onToggle,
  onEdit,
  onDelete,
}: {
  task: Task;
  expanded: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [showAgentMenu, setShowAgentMenu] = useState(false);
  const [showPriorityMenu, setShowPriorityMenu] = useState(false);
  const priority = task.priority || "medium";

  return (
    <div
      draggable
      onDragStart={(e) => e.dataTransfer.setData("taskId", task.id)}
      onClick={onToggle}
      className={cn(
        "bg-white dark:bg-slate-800 rounded-lg p-3 shadow-sm border border-slate-200 dark:border-slate-700 cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow border-l-[3px]",
        PRIORITY_COLORS[priority]
      )}
    >
      <div className="flex items-start gap-2">
        <GripVertical size={14} className="text-slate-300 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          {/* Title row with agent avatar */}
          <div className="flex items-start justify-between gap-1">
            <p className="text-sm font-medium text-slate-900 dark:text-white truncate flex-1">
              {task.title}
            </p>
            <div className="relative shrink-0">
              {task.agent_id ? (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowAgentMenu(!showAgentMenu);
                  }}
                  className="hover:ring-2 hover:ring-istara-300 rounded-full"
                  aria-label="Change assigned agent"
                >
                  <AgentMiniAvatar agentId={task.agent_id} />
                </button>
              ) : (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowAgentMenu(!showAgentMenu);
                  }}
                  className="w-6 h-6 rounded-full border-2 border-dashed border-slate-300 dark:border-slate-600 flex items-center justify-center hover:border-istara-400 transition-colors"
                  aria-label="Assign agent"
                >
                  <Plus size={10} className="text-slate-400" />
                </button>
              )}
              {showAgentMenu && (
                <AgentAssignMenu
                  taskId={task.id}
                  currentAgentId={task.agent_id}
                  onClose={() => setShowAgentMenu(false)}
                />
              )}
            </div>
          </div>

          {/* Badges row */}
          <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
            {task.skill_name && (
              <span className="inline-block text-[10px] bg-istara-100 dark:bg-istara-900/30 text-istara-700 dark:text-istara-400 rounded px-1.5 py-0.5">
                {task.skill_name}
              </span>
            )}
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowPriorityMenu(!showPriorityMenu);
                }}
                className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600"
                aria-label="Change priority"
              >
                <span className={cn("w-1.5 h-1.5 rounded-full", PRIORITY_DOT_COLORS[priority])} />
                {PRIORITY_LABELS[priority]}
                <ChevronDown size={8} />
              </button>
              {showPriorityMenu && (
                <PriorityPicker
                  taskId={task.id}
                  currentPriority={priority}
                  onClose={() => setShowPriorityMenu(false)}
                />
              )}
            </div>
            {/* Document/URL indicators */}
            {((task.input_document_ids?.length || 0) + (task.output_document_ids?.length || 0)) > 0 && (
              <span className="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400" title="Attached documents">
                <FileText size={10} />
                {(task.input_document_ids?.length || 0) + (task.output_document_ids?.length || 0)}
              </span>
            )}
            {(task.urls?.length || 0) > 0 && (
              <span className="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400" title="URLs to fetch">
                <Globe size={10} />
                {task.urls.length}
              </span>
            )}
          </div>

          {/* Progress bar */}
          {task.progress > 0 && task.progress < 1 && (
            <div className="mt-2">
              <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5">
                <div
                  className="bg-istara-500 h-1.5 rounded-full transition-all"
                  style={{ width: `${task.progress * 100}%` }}
                />
              </div>
              <span className="text-[10px] text-slate-400 mt-0.5">
                {Math.round(task.progress * 100)}%
              </span>
            </div>
          )}

          {/* Expanded details */}
          {expanded && (
            <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-700 space-y-2">
              {task.description && (
                <p className="text-xs text-slate-500">{task.description}</p>
              )}
              {task.agent_notes && (
                <div className="text-xs">
                  <span className="flex items-center gap-1 text-slate-400 mb-0.5">
                    <Bot size={10} /> Agent notes
                  </span>
                  <p className="text-slate-600 dark:text-slate-300">
                    {task.agent_notes}
                  </p>
                </div>
              )}
              {task.instructions && (
                <div className="text-xs">
                  <span className="flex items-center gap-1 text-slate-400 mb-0.5">
                    Instructions
                  </span>
                  <p className="text-slate-600 dark:text-slate-300">
                    {task.instructions}
                  </p>
                </div>
              )}
              {task.user_context && (
                <div className="text-xs">
                  <span className="flex items-center gap-1 text-slate-400 mb-0.5">
                    <User size={10} /> Your context
                  </span>
                  <p className="text-slate-600 dark:text-slate-300">
                    {task.user_context}
                  </p>
                </div>
              )}
              {(task.urls?.length || 0) > 0 && (
                <div className="text-xs">
                  <span className="flex items-center gap-1 text-slate-400 mb-0.5">
                    <Globe size={10} /> URLs
                  </span>
                  <div className="space-y-0.5">
                    {task.urls.map((url, i) => (
                      <a key={i} href={url} target="_blank" rel="noopener noreferrer"
                        className="block text-istara-600 dark:text-istara-400 truncate hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >{url}</a>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex items-center gap-3">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onEdit();
                  }}
                  className="text-xs text-istara-600 hover:text-istara-700 font-medium"
                >
                  Edit
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete();
                  }}
                  className="flex items-center gap-1 text-xs text-red-500 hover:text-red-600"
                >
                  <Trash2 size={10} /> Delete
                </button>
              </div>
            </div>
          )}
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
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [editingTask, setEditingTask] = useState<string | null>(null);

  useEffect(() => {
    if (activeProjectId) {
      fetchTasks(activeProjectId);
    }
  }, [activeProjectId, fetchTasks]);

  // Fetch agents for assignment dropdown
  useEffect(() => {
    if (agents.length === 0) fetchAgents();
  }, [agents.length, fetchAgents]);

  const handleCreate = async (status: TaskStatus) => {
    if (!newTaskTitle.trim() || !activeProjectId) return;
    await createTask(activeProjectId, newTaskTitle.trim());
    if (status !== "backlog") {
      const allTasks = useTaskStore.getState().tasks;
      const latest = allTasks[allTasks.length - 1];
      if (latest) await moveTask(latest.id, status);
    }
    setNewTaskTitle("");
    setAddingTo(null);
  };

  const handleDrop = async (taskId: string, newStatus: TaskStatus) => {
    await moveTask(taskId, newStatus);
  };

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <p>Select a project to see tasks.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-x-auto p-4">
      <ViewOnboarding viewId="tasks" title="Research Workflow" description="Kanban board of research tasks. Agents create tasks when you upload files. Drag to reorder, attach documents, track progress." chatPrompt="How do tasks work?" />
      <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Tasks</h2>

      <div className="flex gap-4 min-w-max">
        {COLUMNS.map((col) => {
          const columnTasks = tasks.filter((t) => t.status === col.id);

          return (
            <div
              key={col.id}
              className={cn(
                "w-72 flex-shrink-0 rounded-lg bg-slate-50 dark:bg-slate-900 border-t-4",
                col.color
              )}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const taskId = e.dataTransfer.getData("taskId");
                if (taskId) handleDrop(taskId, col.id);
              }}
            >
              {/* Column header */}
              <div className="flex items-center justify-between p-3 pb-2">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-sm text-slate-700 dark:text-slate-300">
                    {statusLabel(col.id)}
                  </h3>
                  <span className="text-xs bg-slate-200 dark:bg-slate-700 px-1.5 py-0.5 rounded-full text-slate-500">
                    {columnTasks.length}
                  </span>
                </div>
                <button
                  onClick={() => setAddingTo(addingTo === col.id ? null : col.id)}
                  aria-label={`Add task to ${statusLabel(col.id)}`}
                  className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400"
                >
                  <Plus size={14} />
                </button>
              </div>

              {/* New task input */}
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
                    className="w-full px-2 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                    autoFocus
                  />
                </div>
              )}

              {/* Task cards */}
              <div className="p-2 space-y-2 min-h-[100px]">
                {columnTasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    expanded={expandedTask === task.id}
                    onToggle={() => setExpandedTask(expandedTask === task.id ? null : task.id)}
                    onEdit={() => setEditingTask(task.id)}
                    onDelete={() => setDeleteConfirm(task.id)}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Task editor modal */}
      {editingTask && (() => {
        const task = tasks.find((t) => t.id === editingTask);
        return task ? (
          <TaskEditor
            task={task}
            onClose={() => { setEditingTask(null); if (activeProjectId) fetchTasks(activeProjectId); }}
          />
        ) : null;
      })()}

      {/* Delete confirmation */}
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
