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
  moveTask: (taskId: string, status: TaskStatus) => Promise<void>;
  updateTask: (taskId: string, data: Record<string, unknown>) => Promise<void>;
  deleteTask: (taskId: string) => Promise<void>;

  byStatus: (status: TaskStatus) => Task[];
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: [],
  loading: false,
  error: null,

  fetchTasks: async (projectId) => {
    set({ loading: true, error: null });
    try {
      const data = await tasksApi.list(projectId);
      set({ tasks: data, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  createTask: async (projectId, title, description) => {
    const task = await tasksApi.create({ project_id: projectId, title, description });
    set((s) => ({ tasks: [...s.tasks, task] }));
    return task;
  },

  moveTask: async (taskId, status) => {
    const updated = await tasksApi.move(taskId, status);
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === taskId ? updated : t)),
    }));
  },

  updateTask: async (taskId, data) => {
    const updated = await tasksApi.update(taskId, data);
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === taskId ? updated : t)),
    }));
  },

  deleteTask: async (taskId) => {
    await tasksApi.delete(taskId);
    set((s) => ({ tasks: s.tasks.filter((t) => t.id !== taskId) }));
  },

  byStatus: (status) => get().tasks.filter((t) => t.status === status),
}));
