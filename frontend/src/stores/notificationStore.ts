"use client";

import { create } from "zustand";
import { notificationsApi } from "@/lib/api";
import { useProjectStore } from "@/stores/projectStore";
import type { AppNotification, NotificationPreference } from "@/lib/types";

type NotificationsTab = "all" | "preferences";

interface NotificationFilters {
  categories: string[];
  severities: string[];
  agent_id: string;
  search: string;
  from_date: string;
  to_date: string;
  unread_only: boolean;
}

interface NotificationStore {
  activeTab: NotificationsTab;
  notifications: AppNotification[];
  unreadCount: number;
  preferences: NotificationPreference[];
  loading: boolean;
  error: string | null;
  filters: NotificationFilters;
  page: number;
  totalPages: number;
  total: number;

  setActiveTab: (tab: NotificationsTab) => void;
  fetchNotifications: (page?: number, projectId?: string | null) => Promise<void>;
  fetchUnreadCount: (projectId?: string | null) => Promise<void>;
  markRead: (id: string, projectId?: string | null) => Promise<void>;
  markAllRead: (projectId?: string | null) => Promise<void>;
  deleteNotification: (id: string, projectId?: string | null) => Promise<void>;
  fetchPreferences: () => Promise<void>;
  updatePreferences: (prefs: NotificationPreference[]) => Promise<void>;
  setFilter: (key: string, value: any) => void;
  clearFilters: () => void;
  addRealtimeNotification: (notification: AppNotification) => void;
}

const DEFAULT_FILTERS: NotificationFilters = {
  categories: [],
  severities: [],
  agent_id: "",
  search: "",
  from_date: "",
  to_date: "",
  unread_only: false,
};

export const useNotificationStore = create<NotificationStore>((set, get) => ({
  activeTab: "all",
  notifications: [],
  unreadCount: 0,
  preferences: [],
  loading: false,
  error: null,
  filters: { ...DEFAULT_FILTERS },
  page: 1,
  totalPages: 1,
  total: 0,

  setActiveTab: (tab) => set({ activeTab: tab }),

  fetchNotifications: async (page = 1, projectId) => {
    set({ loading: true, error: null });
    if (!projectId) {
      set({ notifications: [], page, totalPages: 1, total: 0, loading: false });
      return;
    }
    try {
      const filters = get().filters;
      const params: Record<string, string | number | boolean> = { page, page_size: 20 };
      if (filters.categories.length > 0) params.categories = filters.categories.join(",");
      if (filters.severities.length > 0) params.severities = filters.severities.join(",");
      if (filters.agent_id) params.agent_id = filters.agent_id;
      params.project_id = projectId;
      if (filters.search) params.search = filters.search;
      if (filters.from_date) params.from_date = filters.from_date;
      if (filters.to_date) params.to_date = filters.to_date;
      if (filters.unread_only) params.unread_only = true;
      const data = await notificationsApi.list(params);
      const notifications = (Array.isArray(data) ? data : data?.notifications || []).map((n: any) => ({
        ...n,
        metadata: n.metadata || n.metadata_json || {},
      }));
      const total = data?.total || notifications.length;
      const totalPages = data?.total_pages || Math.max(1, Math.ceil(total / 20));
      set({ notifications, page, totalPages, total, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  fetchUnreadCount: async (projectId) => {
    if (!projectId) {
      set({ unreadCount: 0 });
      return;
    }
    try {
      const data = await notificationsApi.unreadCount(projectId);
      set({ unreadCount: data.count });
    } catch {
      // silent
    }
  },

  markRead: async (id, projectId) => {
    if (!projectId) {
      set({ error: "Select a project before marking a notification read." });
      return;
    }
    try {
      await notificationsApi.markRead(id, projectId);
      set((s) => ({
        notifications: s.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
        unreadCount: Math.max(
          0,
          s.unreadCount - (s.notifications.find((n) => n.id === id && !n.read) ? 1 : 0)
        ),
      }));
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  markAllRead: async (projectId) => {
    if (!projectId) {
      set({ error: "Select a project before marking notifications read." });
      return;
    }
    try {
      await notificationsApi.markAllRead(projectId);
      set((s) => ({
        notifications: s.notifications.map((n) => ({ ...n, read: true })),
        unreadCount: 0,
      }));
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  deleteNotification: async (id, projectId) => {
    if (!projectId) {
      set({ error: "Select a project before deleting a notification." });
      return;
    }
    try {
      await notificationsApi.delete(id, projectId);
      set((s) => ({
        notifications: s.notifications.filter((n) => n.id !== id),
        unreadCount: Math.max(
          0,
          s.unreadCount - (s.notifications.find((n) => n.id === id && !n.read) ? 1 : 0)
        ),
        total: Math.max(0, s.total - 1),
      }));
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  fetchPreferences: async () => {
    set({ loading: true, error: null });
    try {
      const data = await notificationsApi.preferences();
      const preferences = Array.isArray(data) ? data : data?.preferences || [];
      set({ preferences, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  updatePreferences: async (prefs) => {
    set({ loading: true, error: null });
    try {
      await notificationsApi.updatePreferences(prefs);
      set({ preferences: prefs, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  setFilter: (key, value) => {
    set((s) => ({
      filters: { ...s.filters, [key]: value },
    }));
  },

  clearFilters: () => {
    set({ filters: { ...DEFAULT_FILTERS } });
  },

  addRealtimeNotification: (notification) => {
    const activeProjectId = useProjectStore.getState().activeProjectId;
    if (!activeProjectId || notification.project_id !== activeProjectId) return;
    set((s) => ({
      notifications: [notification, ...s.notifications],
      unreadCount: s.unreadCount + 1,
      total: s.total + 1,
    }));
  },
}));
