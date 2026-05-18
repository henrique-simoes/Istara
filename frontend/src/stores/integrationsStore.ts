"use client";

import { create } from "zustand";
import { channels, deployments, surveys, mcp } from "@/lib/api";
import type { ChannelInstance, ResearchDeployment, SurveyIntegration, MCPServerConfig } from "@/lib/types";

type IntegrationsTab = "overview" | "messaging" | "surveys" | "mcp" | "deployments";

interface IntegrationsStore {
  activeTab: IntegrationsTab;
  // Channels
  channelInstances: ChannelInstance[];
  selectedInstanceId: string | null;
  channelLoading: boolean;
  // Deployments
  deploymentsList: ResearchDeployment[];
  selectedDeploymentId: string | null;
  deploymentLoading: boolean;
  // Surveys
  surveyIntegrations: SurveyIntegration[];
  surveyLoading: boolean;
  // MCP
  mcpServerStatus: any | null;
  mcpClients: MCPServerConfig[];
  mcpLoading: boolean;
  // Error
  error: string | null;

  setActiveTab: (tab: IntegrationsTab) => void;
  fetchChannels: (platform?: string, projectId?: string | null) => Promise<void>;
  fetchDeployments: (projectId?: string | null) => Promise<void>;
  fetchSurveyIntegrations: (projectId?: string | null) => Promise<void>;
  fetchMCPStatus: () => Promise<void>;
  fetchMCPClients: (projectId?: string | null) => Promise<void>;
  selectInstance: (id: string | null) => void;
  selectDeployment: (id: string | null) => void;
}

export const useIntegrationsStore = create<IntegrationsStore>((set) => ({
  activeTab: "overview",
  channelInstances: [],
  selectedInstanceId: null,
  channelLoading: false,
  deploymentsList: [],
  selectedDeploymentId: null,
  deploymentLoading: false,
  surveyIntegrations: [],
  surveyLoading: false,
  mcpServerStatus: null,
  mcpClients: [],
  mcpLoading: false,
  error: null,

  setActiveTab: (tab) => set({ activeTab: tab }),

  fetchChannels: async (platform, projectId) => {
    set({ channelLoading: true, error: null });
    if (!projectId) {
      set({ channelInstances: [], channelLoading: false });
      return;
    }
    try {
      const list = await channels.list(platform, projectId);
      set({ channelInstances: list, channelLoading: false });
    } catch (e: any) {
      set({ channelLoading: false, error: e.message });
    }
  },

  fetchDeployments: async (projectId) => {
    set({ deploymentLoading: true, error: null });
    if (!projectId) {
      set({ deploymentsList: [], selectedDeploymentId: null, deploymentLoading: false });
      return;
    }
    try {
      const list = await deployments.list(projectId);
      set({ deploymentsList: list, deploymentLoading: false });
    } catch (e: any) {
      set({ deploymentLoading: false, error: e.message });
    }
  },

  fetchSurveyIntegrations: async (projectId) => {
    set({ surveyLoading: true, error: null });
    if (!projectId) {
      set({ surveyIntegrations: [], surveyLoading: false });
      return;
    }
    try {
      const list = await surveys.integrations.list(projectId);
      set({ surveyIntegrations: list, surveyLoading: false });
    } catch (e: any) {
      set({ surveyLoading: false, error: e.message });
    }
  },

  fetchMCPStatus: async () => {
    set({ mcpLoading: true, error: null });
    try {
      const status = await mcp.server.status();
      set({ mcpServerStatus: status, mcpLoading: false });
    } catch (e: any) {
      set({ mcpLoading: false, error: e.message });
    }
  },

  fetchMCPClients: async (projectId) => {
    if (!projectId) {
      set({ mcpClients: [] });
      return;
    }
    try {
      const list = await mcp.clients.list(projectId);
      set({ mcpClients: list });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  selectInstance: (id) => set({ selectedInstanceId: id }),
  selectDeployment: (id) => set({ selectedDeploymentId: id }),
}));
