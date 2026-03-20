"use client";

import { create } from "zustand";
import type { ReclawDocument, DocumentTag, DocumentStats } from "@/lib/types";
import { documents as documentsApi } from "@/lib/api";

interface DocumentStore {
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
  setSearchQuery: (query: string) => void;
  setFilterPhase: (phase: string) => void;
  setFilterTag: (tag: string) => void;
  setFilterSource: (source: string) => void;
  selectDocument: (id: string | null) => void;
  deleteDocument: (id: string) => Promise<void>;
  updateDocument: (id: string, data: Record<string, unknown>) => Promise<void>;
}

export const useDocumentStore = create<DocumentStore>((set, get) => ({
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
    set({ loading: true, error: null });
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
      set({
        documents: data.documents,
        total: data.total,
        page: data.page,
        totalPages: data.total_pages,
        loading: false,
      });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  fetchTags: async (projectId) => {
    try {
      const data = await documentsApi.tags(projectId);
      set({ tags: data.tags });
    } catch {
      // silent
    }
  },

  fetchStats: async (projectId) => {
    try {
      const data = await documentsApi.stats(projectId);
      set({ stats: data });
    } catch {
      // silent
    }
  },

  syncDocuments: async (projectId) => {
    try {
      const data = await documentsApi.sync(projectId);
      if (data.synced > 0) {
        // Refresh the list
        await get().fetchDocuments(projectId);
      }
      return data.synced;
    } catch {
      return 0;
    }
  },

  setSearchQuery: (query) => set({ searchQuery: query }),
  setFilterPhase: (phase) => set({ filterPhase: phase }),
  setFilterTag: (tag) => set({ filterTag: tag }),
  setFilterSource: (source) => set({ filterSource: source }),
  selectDocument: (id) => set({ selectedDocId: id }),

  deleteDocument: async (id) => {
    await documentsApi.delete(id);
    set((s) => ({
      documents: s.documents.filter((d) => d.id !== id),
      total: s.total - 1,
      selectedDocId: s.selectedDocId === id ? null : s.selectedDocId,
    }));
  },

  updateDocument: async (id, data) => {
    const updated = await documentsApi.update(id, data);
    set((s) => ({
      documents: s.documents.map((d) => (d.id === id ? updated : d)),
    }));
  },
}));
