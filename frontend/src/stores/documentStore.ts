"use client";

import { create } from "zustand";
import type { ReclawDocument, DocumentTag, DocumentStats } from "@/lib/types";
import { documents as documentsApi } from "@/lib/api";

interface DocumentStore {
  projectId: string | null;
  documents: ReclawDocument[];
  tags: DocumentTag[];
  stats: DocumentStats | null;
  loading: boolean;
  error: string | null;
  total: number;
  page: number;
  totalPages: number;

  // Filters
  searchQuery: string;
  filterPhase: string;
  filterTag: string;
  filterSource: string;

  // Selected document (for preview)
  selectedDocId: string | null;

  // Actions
  fetchDocuments: (projectId: string, page?: number) => Promise<void>;
  fetchTags: (projectId: string) => Promise<void>;
  fetchStats: (projectId: string) => Promise<void>;
  syncDocuments: (projectId: string) => Promise<number>;
  resetProject: (projectId?: string | null) => void;
  setSearchQuery: (query: string) => void;
  setFilterPhase: (phase: string) => void;
  setFilterTag: (tag: string) => void;
  setFilterSource: (source: string) => void;
  selectDocument: (id: string | null) => void;
  deleteDocument: (id: string, projectId: string) => Promise<void>;
  updateDocument: (id: string, projectId: string, data: Record<string, unknown>) => Promise<void>;
}

export const useDocumentStore = create<DocumentStore>((set, get) => ({
  projectId: null,
  documents: [],
  tags: [],
  stats: null,
  loading: false,
  error: null,
  total: 0,
  page: 1,
  totalPages: 0,

  searchQuery: "",
  filterPhase: "",
  filterTag: "",
  filterSource: "",

  selectedDocId: null,

  fetchDocuments: async (projectId, page = 1) => {
    set((s) => ({
      projectId,
      loading: true,
      error: null,
      ...(s.projectId === projectId
        ? {}
        : {
            documents: [],
            tags: [],
            stats: null,
            total: 0,
            page: 1,
            totalPages: 0,
            selectedDocId: null,
          }),
    }));
    try {
      const { searchQuery, filterPhase, filterTag, filterSource } = get();
      const data = await documentsApi.list({
        project_id: projectId,
        phase: filterPhase || undefined,
        tag: filterTag || undefined,
        source: filterSource || undefined,
        search: searchQuery || undefined,
        page,
        page_size: 50,
      });
      if (get().projectId !== projectId) return;
      set({
        documents: data.documents.filter((doc) => doc.project_id === projectId),
        total: data.total,
        page: data.page,
        totalPages: data.total_pages,
        loading: false,
      });
    } catch (e: any) {
      if (get().projectId !== projectId) return;
      set({ error: e.message, loading: false });
    }
  },

  fetchTags: async (projectId) => {
    try {
      const data = await documentsApi.tags(projectId);
      if (get().projectId !== projectId) return;
      set({ tags: data.tags });
    } catch {
      // silent
    }
  },

  fetchStats: async (projectId) => {
    try {
      const data = await documentsApi.stats(projectId);
      if (get().projectId !== projectId) return;
      set({ stats: data });
    } catch {
      // silent
    }
  },

  syncDocuments: async (projectId) => {
    set({ error: null });
    try {
      const data = await documentsApi.sync(projectId);
      if (get().projectId !== projectId) return 0;
      if (data.synced > 0) {
        // Refresh the list
        await get().fetchDocuments(projectId);
      }
      return data.synced;
    } catch (e: any) {
      if (get().projectId !== projectId) return 0;
      set({ error: e.message || "Could not sync project documents." });
      return 0;
    }
  },

  resetProject: (projectId = null) =>
    set({
      projectId,
      documents: [],
      tags: [],
      stats: null,
      loading: false,
      error: null,
      total: 0,
      page: 1,
      totalPages: 0,
      selectedDocId: null,
    }),

  setSearchQuery: (query) => set({ searchQuery: query }),
  setFilterPhase: (phase) => set({ filterPhase: phase }),
  setFilterTag: (tag) => set({ filterTag: tag }),
  setFilterSource: (source) => set({ filterSource: source }),
  selectDocument: (id) => set({ selectedDocId: id }),

  deleteDocument: async (id, projectId) => {
    set({ error: null });
    try {
      await documentsApi.delete(id, projectId);
      set((s) => ({
        documents: s.documents.filter((d) => d.id !== id),
        total: Math.max(0, s.total - 1),
        selectedDocId: s.selectedDocId === id ? null : s.selectedDocId,
      }));
    } catch (e: any) {
      set({ error: e.message || "Could not delete document." });
      throw e;
    }
  },

  updateDocument: async (id, projectId, data) => {
    set({ error: null });
    try {
      const updated = await documentsApi.update(id, projectId, data);
      if (updated.project_id !== projectId || get().projectId !== projectId) return;
      set((s) => ({
        documents: s.documents.map((d) => (d.id === id ? updated : d)),
      }));
    } catch (e: any) {
      set({ error: e.message || "Could not update document." });
      throw e;
    }
  },
}));
