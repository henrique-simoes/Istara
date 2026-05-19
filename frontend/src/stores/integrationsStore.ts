"use client";

import { create } from "zustand";
import { channels, deployments, surveys, mcp } from "@/lib/api";
import type { ChannelInstance, ResearchDeployment, SurveyIntegration, MCPServerConfig } from "@/lib/types";

type IntegrationsTab = "overview" | "messaging" | "surveys" | "mcp" | "deployments";

type ProjectOwned = { project_id?: string | null };

const filterByProject = <T extends ProjectOwned>(items: T[], projectId: string): T[] =>
  items.filter((item) => item.project_id === projectId);

const normalizedEndpointKey = (value: string | null | undefined): string =>
  (value || "").trim().replace(/\/+$/, "").toLowerCase();

const dedupeProjectMCPClients = (items: MCPServerConfig[], projectId: string): MCPServerConfig[] => {
  const scoped = filterByProject(items, projectId);
  const seen = new Set<string>();
  return scoped.filter((client) => {
    const key = [
      client.project_id,
      normalizedEndpointKey(client.transport),
      normalizedEndpointKey(client.url || client.id),
    ].join(":");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

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
    set({ channelInstances: [], selectedInstanceId: null, channelLoading: true, error: null });
    if (!projectId) {
      set({ channelInstances: [], channelLoading: false });
      return;
    }
    try {
      const list = await channels.list(platform, projectId);
      const scoped = filterByProject(list, projectId);
      set({ channelInstances: scoped, channelLoading: false });
    } catch (e: any) {
      set({ channelInstances: [], selectedInstanceId: null, channelLoading: false, error: e.message });
    }
  },

  fetchDeployments: async (projectId) => {
    set({ deploymentsList: [], selectedDeploymentId: null, deploymentLoading: true, error: null });
    if (!projectId) {
      set({ deploymentsList: [], selectedDeploymentId: null, deploymentLoading: false });
      return;
    }
    try {
      const list = await deployments.list(projectId);
      const scoped = filterByProject(list, projectId);
      set({ deploymentsList: scoped, deploymentLoading: false });
    } catch (e: any) {
      set({ deploymentsList: [], selectedDeploymentId: null, deploymentLoading: false, error: e.message });
    }
  },

  fetchSurveyIntegrations: async (projectId) => {
    set({ surveyIntegrations: [], surveyLoading: true, error: null });
    if (!projectId) {
      set({ surveyIntegrations: [], surveyLoading: false });
      return;
    }
    try {
      const list = await surveys.integrations.list(projectId);
      const scoped = filterByProject(list, projectId);
      set({ surveyIntegrations: scoped, surveyLoading: false });
    } catch (e: any) {
      set({ surveyIntegrations: [], surveyLoading: false, error: e.message });
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
    set({ mcpClients: [], mcpLoading: true, error: null });
    if (!projectId) {
      set({ mcpClients: [], mcpLoading: false });
      return;
    }
    try {
      const list = await mcp.clients.list(projectId);
      const scoped = dedupeProjectMCPClients(list, projectId);
      set({ mcpClients: scoped, mcpLoading: false });
    } catch (e: any) {
      set({ mcpClients: [], mcpLoading: false, error: e.message });
    }
  },

  selectInstance: (id) => set({ selectedInstanceId: id }),
  selectDeployment: (id) => set({ selectedDeploymentId: id }),
}));
