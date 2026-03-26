"use client";

import { create } from "zustand";
import { notificationsApi } from "@/lib/api";
import type { AppNotification, NotificationPreference } from "@/lib/types";

type NotificationsTab = "all" | "preferences";

interface NotificationFilters {
  categories: string[];
  severities: string[];
  agent_id: string;
  project_id: string;
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
  fetchNotifications: (page?: number) => Promise<void>;
  fetchUnreadCount: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  markAllRead: (projectId?: string) => Promise<void>;
  deleteNotification: (id: string) => Promise<void>;
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
  project_id: "",
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

  fetchNotifications: async (page = 1) => {
    set({ loading: true, error: null });
    try {
      const filters = get().filters;
      const params: Record<string, string | number | boolean> = { page, page_size: 20 };
      if (filters.categories.length > 0) params.categories = filters.categories.join(",");
      if (filters.severities.length > 0) params.severities = filters.severities.join(",");
      if (filters.agent_id) params.agent_id = filters.agent_id;
      if (filters.project_id) params.project_id = filters.project_id;
      if (filters.search) params.search = filters.search;
      if (filters.from_date) params.from_date = filters.from_date;
      if (filters.to_date) params.to_date = filters.to_date;
      if (filters.unread_only) params.unread_only = true;
      const data = await notificationsApi.list(params);
      const notifications = Array.isArray(data) ? data : data?.notifications || [];
      const totalPages = data?.total_pages || 1;
      const total = data?.total || notifications.length;
      set({ notifications, page, totalPages, total, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  fetchUnreadCount: async () => {
    try {
      const data = await notificationsApi.unreadCount();
      set({ unreadCount: data.count });
    } catch {
      // silent
    }
  },

  markRead: async (id) => {
    try {
      await notificationsApi.markRead(id);
      set((s) => ({
        notifications: s.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
        unreadCount: Math.max(0, s.unreadCount - 1),
      }));
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  markAllRead: async (projectId) => {
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

  deleteNotification: async (id) => {
    try {
      await notificationsApi.delete(id);
      set((s) => ({
        notifications: s.notifications.filter((n) => n.id !== id),
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
    set((s) => ({
      notifications: [notification, ...s.notifications],
      unreadCount: s.unreadCount + 1,
      total: s.total + 1,
    }));
  },
}));
