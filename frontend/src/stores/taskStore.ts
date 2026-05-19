"use client";

import { create } from "zustand";
import type { Task, TaskStatus } from "@/lib/types";
import { tasks as tasksApi } from "@/lib/api";

interface TaskStore {
  tasks: Task[];
  loading: boolean;
  error: string | null;

  fetchTasks: (projectId: string) => Promise<void>;
  createTask: (projectId: string, title: string, description?: string) => Promise<Task>;
  moveTask: (taskId: string, status: TaskStatus, projectId: string) => Promise<void>;
  updateTask: (taskId: string, data: Record<string, unknown>, projectId: string) => Promise<void>;
  approveTask: (taskId: string, projectId: string, note?: string) => Promise<void>;
  requestRevision: (
    taskId: string,
    data: {
      what_to_review: string;
      next_status: Extract<TaskStatus, "backlog" | "in_progress">;
      severity?: string | null;
      failure_category?: string | null;
      labels?: Task["labels"];
      skill_name?: string | null;
      input_document_ids?: string[];
      urls?: string[];
    },
    projectId: string
  ) => Promise<void>;
  deleteTask: (taskId: string, projectId: string) => Promise<void>;

  byStatus: (status: TaskStatus) => Task[];
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: [],
  loading: false,
  error: null,

  fetchTasks: async (projectId) => {
    if (!projectId) {
      set({ tasks: [], loading: false, error: null });
      return;
    }

    set({ tasks: [], loading: true, error: null });
    try {
      const data = await tasksApi.list(projectId);
      set({ tasks: data.filter((task) => task.project_id === projectId), loading: false });
    } catch (e: any) {
      set({ tasks: [], error: e.message, loading: false });
    }
  },

  createTask: async (projectId, title, description) => {
    const task = await tasksApi.create({ project_id: projectId, title, description });
    set((s) => ({ tasks: [...s.tasks, task] }));
    return task;
  },

  moveTask: async (taskId, status, projectId) => {
    const updated = await tasksApi.move(taskId, status, projectId);
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === taskId ? updated : t)),
    }));
  },

  updateTask: async (taskId, data, projectId) => {
    const updated = await tasksApi.update(taskId, data, projectId);
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === taskId ? updated : t)),
    }));
  },

  approveTask: async (taskId, projectId, note) => {
    const { task } = await tasksApi.approve(taskId, projectId, { note });
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === taskId ? task : t)),
    }));
  },

  requestRevision: async (taskId, data, projectId) => {
    const { task } = await tasksApi.requestRevision(taskId, data, projectId);
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === taskId ? task : t)),
    }));
  },

  deleteTask: async (taskId, projectId) => {
    await tasksApi.delete(taskId, projectId);
    set((s) => ({ tasks: s.tasks.filter((t) => t.id !== taskId) }));
  },

  byStatus: (status) => get().tasks.filter((t) => t.status === status),
}));
