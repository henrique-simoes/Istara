"use client";

import { create } from "zustand";
import { interfaces as interfacesApi } from "@/lib/api";

type InterfacesTab = "design-chat" | "generate" | "screens" | "figma" | "handoff";

interface InterfacesStore {
  activeTab: InterfacesTab;
  screens: any[];
  briefs: any[];
  selectedScreenId: string | null;
  loading: boolean;
  generating: boolean;
  status: any | null;
  error: string | null;
  onboardingDismissed: boolean;
  privacyAcknowledged: boolean;

  // Design chat state
  designMessages: any[];
  designStreaming: boolean;
  designStreamingContent: string;

  setActiveTab: (tab: InterfacesTab) => void;
  fetchStatus: () => Promise<void>;
  fetchScreens: (projectId: string) => Promise<void>;
  fetchBriefs: (projectId: string) => Promise<void>;
  selectScreen: (id: string | null) => void;
  dismissOnboarding: () => void;
  acknowledgePrivacy: () => void;
  sendDesignMessage: (projectId: string, content: string, sessionId?: string) => Promise<void>;
  clearDesignMessages: () => void;
}

const ONBOARDING_KEY = "istara-interfaces-onboarding-dismissed";
const PRIVACY_KEY = "istara-interfaces-privacy-acknowledged";

function getStoredBool(key: string): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(key) === "true";
}

export const useInterfacesStore = create<InterfacesStore>((set, get) => ({
  activeTab: "design-chat",
  screens: [],
  briefs: [],
  selectedScreenId: null,
  loading: false,
  generating: false,
  status: null,
  error: null,
  onboardingDismissed: getStoredBool(ONBOARDING_KEY),
  privacyAcknowledged: getStoredBool(PRIVACY_KEY),
  designMessages: [],
  designStreaming: false,
  designStreamingContent: "",

  setActiveTab: (tab) => set({ activeTab: tab }),

  fetchStatus: async () => {
    try {
      const status = await interfacesApi.status();
      set({ status });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  fetchScreens: async (projectId) => {
    set({ loading: true });
    try {
      const data = await interfacesApi.screens.list(projectId);
      set({ screens: Array.isArray(data) ? data : (data as any).screens || [], loading: false });
    } catch (e: any) {
      set({ loading: false, error: e.message });
    }
  },

  fetchBriefs: async (projectId) => {
    try {
      const data = await interfacesApi.handoff.listBriefs(projectId);
      set({ briefs: data.briefs || [] });
    } catch { /* silent */ }
  },

  selectScreen: (id) => set({ selectedScreenId: id }),

  dismissOnboarding: () => {
    localStorage.setItem(ONBOARDING_KEY, "true");
    set({ onboardingDismissed: true });
  },

  acknowledgePrivacy: () => {
    localStorage.setItem(PRIVACY_KEY, "true");
    set({ privacyAcknowledged: true });
  },

  sendDesignMessage: async (projectId, content, sessionId) => {
    const userMsg = { id: `temp-${Date.now()}`, role: "user", content, created_at: new Date().toISOString() };
    set((s) => ({
      designMessages: [...s.designMessages, userMsg],
      designStreaming: true,
      designStreamingContent: "",
      error: null,
    }));
    try {
      let fullContent = "";
      let messageId = "";
      for await (const event of interfacesApi.designChat.send(projectId, content, sessionId)) {
        if (event.type === "chunk") {
          fullContent += event.content;
          set({ designStreamingContent: fullContent });
        } else if (event.type === "done") {
          messageId = event.message_id;
        } else if (event.type === "error") {
          set({ error: event.message, designStreaming: false });
          return;
        }
      }
      const assistantMsg = {
        id: messageId || `msg-${Date.now()}`,
        role: "assistant",
        content: fullContent,
        created_at: new Date().toISOString(),
        agent_name: "Design Lead",
      };
      set((s) => ({
        designMessages: [...s.designMessages, assistantMsg],
        designStreaming: false,
        designStreamingContent: "",
      }));
    } catch (e: any) {
      set({ error: e.message, designStreaming: false, designStreamingContent: "" });
    }
  },

  clearDesignMessages: () => set({ designMessages: [], designStreamingContent: "" }),
}));
