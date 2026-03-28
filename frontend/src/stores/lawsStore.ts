"use client";

import { create } from "zustand";
import { laws } from "@/lib/api";
import type { UXLaw, ComplianceProfile, LawCategory } from "@/lib/types";

type LawsTab = "catalog" | "compliance";

interface LawsStore {
  activeTab: LawsTab;
  laws: UXLaw[];
  selectedLawId: string | null;
  compliance: ComplianceProfile | null;
  categoryFilter: LawCategory | null;
  searchQuery: string;
  loading: boolean;
  error: string | null;

  setActiveTab: (tab: LawsTab) => void;
  fetchLaws: (category?: string) => Promise<void>;
  fetchCompliance: (projectId: string) => Promise<void>;
  selectLaw: (id: string | null) => void;
  setCategoryFilter: (cat: LawCategory | null) => void;
  setSearchQuery: (q: string) => void;
}

export const useLawsStore = create<LawsStore>((set, get) => ({
  activeTab: "catalog",
  laws: [],
  selectedLawId: null,
  compliance: null,
  categoryFilter: null,
  searchQuery: "",
  loading: false,
  error: null,

  setActiveTab: (tab) => set({ activeTab: tab }),

  fetchLaws: async (category) => {
    set({ loading: true, error: null });
    try {
      const list = await laws.list(category || undefined);
      set({ laws: list, loading: false });
    } catch (e: any) {
      set({ loading: false, error: e.message });
    }
  },

  fetchCompliance: async (projectId) => {
    set({ loading: true, error: null });
    try {
      const profile = await laws.compliance(projectId);
      set({ compliance: profile, loading: false });
    } catch (e: any) {
      set({ loading: false, error: e.message });
    }
  },

  selectLaw: (id) => set({ selectedLawId: id }),
  setCategoryFilter: (cat) => set({ categoryFilter: cat }),
  setSearchQuery: (q) => set({ searchQuery: q }),
}));
