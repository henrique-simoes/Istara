"use client";

import { useCallback, useEffect, useState } from "react";
import { Cpu, HardDrive, Monitor, Wifi, WifiOff, RefreshCw, Plus, Server, Trash2, Users, Lock, Gauge, Download } from "lucide-react";
import { settings as settingsApi, telemetry as telemetryApi, piEndpoints, piCatalogApi, piOAuthApi } from "@/lib/api";
import type { HardwareInfo, ModelRecommendation } from "@/lib/types";
import type { PiEndpoint, PiCatalogProvider, PiCatalogModel, PiOAuthFlow } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import UserManagement from "./UserManagement";
import ConnectionStringPanel from "@/components/settings/ConnectionStringPanel";
import UpdateChecker from "@/components/settings/UpdateChecker";
import GovernedEvolutionView from "@/components/settings/GovernedEvolutionView";
import DonateComputeToggle from "@/components/common/DonateComputeToggle";
import AccountSecurityManager from "@/components/settings/AccountSecurityManager";
import FileEncryptionManager from "@/components/settings/FileEncryptionManager";
import PasskeyManager from "@/components/settings/PasskeyManager";
import TOTPManager from "@/components/settings/TOTPManager";
import SessionManager from "@/components/settings/SessionManager";
import ViewOnboarding from "@/components/common/ViewOnboarding";
import { resetAllOnboarding } from "@/hooks/useViewOnboarding";
import { useRoleCapabilities } from "@/hooks/useRoleCapabilities";
import { mergeModelCatalogs } from "@/lib/modelCatalog";
import { agentEngineLabel } from "@/lib/utils";
import {
  MODEL_PROVIDER_OPTIONS,
  defaultHostForProvider,
  providerLabel,
} from "@/lib/modelProviders";

function formatGb(value?: number | null): string {
  return Number.isFinite(value) && Number(value) > 0
    ? `${Number(value).toFixed(1)} GB`
    : "Unknown";
}

export default function SettingsView() {
  const capabilities = useRoleCapabilities();
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [recommendation, setRecommendation] = useState<ModelRecommendation | null>(null);
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [models, setModels] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const canManageInfrastructure = capabilities.canManageLlmInfrastructure;
  const mergedModels = mergeModelCatalogs(models?.models, models?.pi_catalog);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    const [statusResult, hardwareResult, modelsResult] = await Promise.allSettled([
      settingsApi.status(),
      canManageInfrastructure ? settingsApi.hardware() : Promise.resolve(null),
      canManageInfrastructure ? settingsApi.models() : Promise.resolve(null),
    ]);

    if (statusResult.status === "fulfilled") {
      setSystemStatus(statusResult.value);
    } else {
      console.error("Failed to load settings status:", statusResult.reason);
      setSystemStatus(null);
    }

    if (hardwareResult.status === "fulfilled" && hardwareResult.value) {
      setHardware(hardwareResult.value.hardware);
      setRecommendation(hardwareResult.value.recommendation);
    } else {
      if (hardwareResult.status === "rejected") console.error("Failed to load hardware:", hardwareResult.reason);
      setHardware(null);
      setRecommendation(null);
    }

    if (modelsResult.status === "fulfilled" && modelsResult.value) {
      setModels(modelsResult.value);
    } else {
      if (modelsResult.status === "rejected") console.error("Failed to load models:", modelsResult.reason);
      setModels(null);
    }
    setLoading(false);
  }, [canManageInfrastructure]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <RefreshCw size={20} className="animate-spin mr-2" />
        Loading system info...
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto space-y-6">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-white">⚙️ Settings</h2>
      <ViewOnboarding viewId="settings" title="System Settings" description="Configure model providers, connection strings, authentication factors, sessions, account security, encrypted files, updates, and local compute donation." chatPrompt="What should I configure first in settings?" />

      {/* Software Updates */}
      <UpdateChecker />

      {/* Governed Evolution */}
      {capabilities.canUseGovernedEvolution && <GovernedEvolutionView />}

      {/* Team Members */}
      {capabilities.canManageAuthUsers && (
        <div id="tour-target-user-management">
          <UserManagement />
        </div>
      )}

      {/* Connection Strings (admin only, team mode) */}
      {capabilities.canManageConnectionStrings && <ConnectionStringPanel />}

      {/* Account security */}
      <AccountSecurityManager />

      {/* File and backup encryption */}
      {capabilities.canManageSystemSettings && <FileEncryptionManager />}

      {/* Compute Donation */}
      <DonateComputeToggle />

      {/* Passkey Management */}
      <PasskeyManager />

      {/* Two-Factor Authentication */}
      <TOTPManager />

      {/* Active Auth Sessions */}
      <SessionManager />

      {/* System Status */}
      <div id="tour-target-system-status" className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <h3 className="font-medium text-slate-900 dark:text-white mb-3 flex items-center gap-2">
          <Monitor size={18} />
          System Status
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">Backend:</span>
            <span className="text-sm text-green-600 font-medium">
              {systemStatus?.services?.backend || "unknown"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">
              LLM{models?.provider ? ` (${providerLabel(models.provider)})` : ""}:
            </span>
            {systemStatus?.services?.llm === "connected" ? (
              <span className="flex items-center gap-1 text-sm text-green-600 font-medium">
                <Wifi size={14} /> Connected
              </span>
            ) : (
              <span className="flex items-center gap-1 text-sm text-red-500 font-medium">
                <WifiOff size={14} /> Disconnected
              </span>
            )}
          </div>
          {canManageInfrastructure && models?.agentic_engine_default && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">Agentic Core:</span>
              <select
                aria-label="Global agentic core"
                value={models.agentic_engine_default === "pi" ? "pi" : "istara"}
                onChange={async (e) => {
                  try {
                    await settingsApi.setAgenticEngine(e.target.value as "pi" | "istara");
                    window.dispatchEvent(
                      new CustomEvent("istara:toast", {
                        detail: {
                          type: "success",
                          title: "Agentic Core Switched",
                          message: `Global agentic core is now ${e.target.value === "pi" ? "Pi" : "Istara"}. New calls use it unless a project overrides.`,
                        },
                      })
                    );
                    window.location.reload();
                  } catch (err: any) {
                    window.dispatchEvent(
                      new CustomEvent("istara:toast", {
                        detail: {
                          type: "error",
                          title: "Switch Failed",
                          message: err.message || "Could not switch the agentic core",
                        },
                      })
                    );
                  }
                }}
                className="px-2 py-1 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-istara-500"
              >
                <option value="pi">Pi</option>
                <option value="istara">Istara</option>
              </select>
            </div>
          )}
          {canManageInfrastructure && (
            <>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500">Server Model:</span>
                <span className="text-sm font-mono">{models?.active_model || "—"}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500">Embed Model:</span>
                <span className="text-sm font-mono">{models?.embed_model || "—"}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Hardware */}
      {canManageInfrastructure && hardware && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="font-medium text-slate-900 dark:text-white mb-3 flex items-center gap-2">
            <Cpu size={18} />
            Hardware (Server)
          </h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-slate-500">OS</p>
              <p className="font-medium text-slate-900 dark:text-white">{hardware.os}</p>
            </div>
            <div>
              <p className="text-slate-500">CPU</p>
              <p className="font-medium text-slate-900 dark:text-white">
                {hardware.cpu_cores} cores ({hardware.cpu_arch})
              </p>
            </div>
            <div>
              <p className="text-slate-500">Total RAM</p>
              <p className="font-medium text-slate-900 dark:text-white">{formatGb(hardware.total_ram_gb)}</p>
            </div>
            <div>
              <p className="text-slate-500">Available for Istara</p>
              <p className="font-medium text-istara-600">{formatGb(hardware.istara_ram_budget_gb)}</p>
            </div>
            {hardware.gpu && (
              <>
                <div>
                  <p className="text-slate-500">GPU</p>
                  <p className="font-medium text-slate-900 dark:text-white">{hardware.gpu.name}</p>
                </div>
                <div>
                  <p className="text-slate-500">VRAM</p>
                  <p className="font-medium text-slate-900 dark:text-white">
                    {Math.round(hardware.gpu.vram_mb / 1024)} GB
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Model Recommendation */}
      {canManageInfrastructure && recommendation && (
        <div className="bg-istara-50 dark:bg-istara-900/20 rounded-xl border border-istara-200 dark:border-istara-800 p-5">
          <h3 className="font-medium text-istara-800 dark:text-istara-300 mb-3 flex items-center gap-2">
            <HardDrive size={18} />
            Recommended Model
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-istara-600 dark:text-istara-400">Model</p>
              <p className="font-bold font-mono text-istara-800 dark:text-istara-200">
                {recommendation.model_name}
              </p>
            </div>
            <div>
              <p className="text-istara-600 dark:text-istara-400">Quantization</p>
              <p className="font-medium font-mono">{recommendation.quantization}</p>
            </div>
            <div>
              <p className="text-istara-600 dark:text-istara-400">Context Length</p>
              <p className="font-medium">{recommendation.context_length.toLocaleString()} tokens</p>
            </div>
            <div>
              <p className="text-istara-600 dark:text-istara-400">GPU Layers</p>
              <p className="font-medium">
                {recommendation.gpu_layers === -1 ? "All (full offload)" : recommendation.gpu_layers}
              </p>
            </div>
          </div>
          <p className="mt-3 text-xs text-istara-600 dark:text-istara-400 italic">
            {recommendation.reason}
          </p>
        </div>
      )}

      {/* Available Models */}
      {canManageInfrastructure && mergedModels.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="font-medium text-slate-900 dark:text-white mb-3">Available Models</h3>
          <div className="space-y-2">
            {mergedModels.map((model) => {
              const label = providerLabel(typeof model.provider_type === "string" ? model.provider_type : null);
              return (
                <div
                  key={`${model.engine}-${model.endpoint_id || model.name}-${model.server_name || ""}`}
                  className="flex items-center justify-between py-2 px-3 rounded-lg bg-slate-50 dark:bg-slate-900"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-mono font-medium text-slate-900 dark:text-white">
                      {model.name}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {model.size && (
                        <span className="text-xs text-slate-400">
                          {(model.size / 1e9).toFixed(1)} GB
                        </span>
                      )}
                      {model.server_name && (
                        <span className="inline-flex items-center gap-1 text-xs bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded px-1.5 py-0.5">
                          <Server size={10} />
                          {model.server_name}
                        </span>
                      )}
                      <span className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded px-1.5 py-0.5">
                        {label}
                      </span>
                    </div>
                  </div>
                  {model.engine === "pi" ? (
                    <span
                      aria-label="Pi catalog model"
                      className="text-xs bg-istara-100 dark:bg-istara-900/30 text-istara-700 dark:text-istara-400 rounded-full px-2 py-0.5 ml-2 shrink-0"
                    >
                      Available to Pi
                    </span>
                  ) : model.name === models.active_model ? (
                    <span className="text-xs bg-istara-100 dark:bg-istara-900/30 text-istara-700 dark:text-istara-400 rounded-full px-2 py-0.5 ml-2 shrink-0">
                      Active
                    </span>
                  ) : model.switchable ? (
                    <button
                      onClick={async () => {
                        try {
                          await settingsApi.switchModel(model.name);
                          await fetchAll();
                        } catch (e) {
                          console.error("Failed to switch model:", e);
                        }
                      }}
                      className="text-xs px-3 py-1 rounded-lg bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-istara-100 hover:text-istara-700 transition-colors ml-2 shrink-0"
                    >
                      Switch
                    </button>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Pull new model */}
      {canManageInfrastructure && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="font-medium text-slate-900 dark:text-white mb-2">Pull New Model</h3>
          <p className="text-xs text-slate-500 mb-3">
            {models?.provider === "lmstudio"
              ? "Load models through LM Studio's UI, or enter a model name to switch."
              : models?.provider === "ollama"
              ? "Download a new model from the Ollama registry."
              : "Use the provider's model manager, or enter an advertised model name to switch."}
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="e.g., qwen3:7b, llama3:8b, mistral:latest"
              className="flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-istara-500"
              onKeyDown={async (e) => {
                if (e.key === "Enter") {
                  const input = e.target as HTMLInputElement;
                  const model = input.value.trim();
                  if (model) {
                    try {
                      await settingsApi.switchModel(model);
                      input.value = "";
                      await fetchAll();
                    } catch (err) {
                      console.error("Failed to pull model:", err);
                    }
                  }
                }
              }}
            />
          </div>
        </div>
      )}

      {/* Pi Model Management — replaces the legacy LLM Servers section (owner decision 2026-08-23) */}
      {capabilities.canManageLlmInfrastructure && <PiEndpointsSection />}

      {/* Telemetry (Local-first, No phone-home) */}
      {capabilities.canManageTelemetry && <TelemetrySection />}

      {/* Team Mode */}
      {capabilities.canManageSystemSettings && (
        <div id="tour-target-team-mode" className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="font-medium text-slate-900 dark:text-white mb-3 flex items-center gap-2">
            <Users size={18} />
            Team Mode
          </h3>
          <p className="text-sm text-slate-500 mb-3">
            Enable team mode to allow multiple users to connect, authenticate, and collaborate on research projects.
            First registered user becomes admin.
          </p>
          <div className="flex items-center gap-3 mb-3">
            <button
              onClick={async () => {
                const newState = !systemStatus?.team_mode;
                try {
                  await settingsApi.toggleTeamMode(newState);
                  await fetchAll();
                  // Refresh auth store so UserManagement appears/disappears
                  await useAuthStore.getState().checkTeamStatus();
                  await useAuthStore.getState().fetchMe();
                  // Notify guided tour
                  window.dispatchEvent(new CustomEvent("istara:team-mode-toggled", { detail: { enabled: newState } }));
                } catch (e) {
                  console.error("Failed to toggle team mode:", e);
                }
              }}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                systemStatus?.team_mode
                  ? "bg-istara-600"
                  : "bg-slate-300 dark:bg-slate-600"
              }`}
              role="switch"
              aria-checked={systemStatus?.team_mode || false}
              aria-label="Toggle team mode"
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  systemStatus?.team_mode ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              {systemStatus?.team_mode ? "Enabled" : "Disabled"}
            </span>
          </div>
          <div className="text-xs text-slate-400">
            Server restart recommended after changing. In team mode, users register and authenticate with JWT.
          </div>
        </div>
      )}

      {/* Onboarding Hints Reset */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => { resetAllOnboarding(); window.location.reload(); }}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
        >
          <RefreshCw size={14} />
          Reset Onboarding Hints
        </button>
        <button
          onClick={fetchAll}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>
    </div>
  );
}

function TelemetrySection() {
  const [telemetryEnabled, setTelemetryEnabled] = useState(false);
  const [telemetryStats, setTelemetryStats] = useState<{
    total_spans: number;
    total_model_entries: number;
    spans_last_24h: number;
  } | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<string | null>(null);

  const fetchTelemetryStatus = async () => {
    try {
      const data = await telemetryApi.status();
      setTelemetryEnabled(data.telemetry_enabled);
      setTelemetryStats(data.stats);
    } catch {}
  };

  useEffect(() => {
    fetchTelemetryStatus();
  }, []);

  const handleToggle = async () => {
    try {
      const result = await telemetryApi.toggle(!telemetryEnabled);
      setTelemetryEnabled(result.telemetry_enabled);
    } catch {}
  };

  const handleExport = async () => {
    setExporting(true);
    setExportResult(null);
    try {
      const result = await telemetryApi.export(undefined, 7, true);
      setExportResult(`Exported ${result.span_count} spans to ${result.export_dir}`);
    } catch (e: any) {
      setExportResult(`Export failed: ${e.message}`);
    }
    setExporting(false);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
          <Gauge size={18} />
          Local Telemetry
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExport}
            disabled={exporting || !telemetryEnabled}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Download size={12} />
            {exporting ? "Exporting..." : "Export"}
          </button>
          <button
            onClick={handleToggle}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              telemetryEnabled ? "bg-istara-600" : "bg-slate-300 dark:bg-slate-600"
            }`}
            role="switch"
            aria-checked={telemetryEnabled}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                telemetryEnabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>
      </div>

      <p className="text-sm text-slate-500 mb-3">
        Record model performance, latency, and tool success rates to enable the Model Intelligence dashboard.
        <strong> No data ever leaves your machine</strong> unless you manually export and share it.
      </p>

      <div className="grid grid-cols-3 gap-4 mb-3">
        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-3 text-center">
          <div className="text-xs text-slate-400 mb-1">Total Spans</div>
          <div className="text-lg font-bold text-slate-700 dark:text-slate-200">
            {telemetryStats?.total_spans.toLocaleString() || 0}
          </div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-3 text-center">
          <div className="text-xs text-slate-400 mb-1">Model Stats</div>
          <div className="text-lg font-bold text-slate-700 dark:text-slate-200">
            {telemetryStats?.total_model_entries.toLocaleString() || 0}
          </div>
        </div>
        <div className="bg-slate-50 dark:bg-slate-900 rounded-lg p-3 text-center">
          <div className="text-xs text-slate-400 mb-1">Last 24h</div>
          <div className="text-lg font-bold text-istara-600">
            {telemetryStats?.spans_last_24h.toLocaleString() || 0}
          </div>
        </div>
      </div>

      {exportResult && (
        <div className="mb-3 text-xs p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded border border-blue-100 dark:border-blue-800 break-all font-mono">
          {exportResult}
        </div>
      )}

      <div className="text-xs text-slate-400">
        Status: <span className={telemetryEnabled ? "text-green-500 font-medium" : "text-slate-500"}>
          {telemetryEnabled ? "Recording active" : "Recording paused"}
        </span>
        {telemetryEnabled && " • Data stored locally in SQLite."}
      </div>
    </div>
  );
}

function PiEndpointsSection() {
  const { user, teamMode } = useAuthStore();
  const [endpoints, setEndpoints] = useState<PiEndpoint[]>([]);
  const [retirementNote, setRetirementNote] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [providers, setProviders] = useState<PiCatalogProvider[]>([]);
  const [providerQuery, setProviderQuery] = useState("");
  const [modelQuery, setModelQuery] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<PiCatalogProvider | null>(null);
  const [selectedModel, setSelectedModel] = useState<PiCatalogModel | null>(null);
  const [loginMethod, setLoginMethod] = useState<"api_key" | "oauth" | "none">("api_key");
  const [apiKey, setApiKey] = useState("");
  const [endpointName, setEndpointName] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  // OAuth state
  const [oauthFlows, setOauthFlows] = useState<PiOAuthFlow[]>([]);
  const [activeOAuth, setActiveOAuth] = useState<PiOAuthFlow | null>(null);
  const [oauthError, setOauthError] = useState<string | null>(null);
  const canManage = !teamMode || user?.role === "admin";

  const fetchEndpoints = useCallback(async () => {
    if (!canManage) return;
    try {
      const data = await piEndpoints.list();
      setEndpoints(data.endpoints || []);
      setRetirementNote(data.retirement_note || "");
    } catch {}
  }, [canManage]);

  const fetchCatalog = useCallback(async () => {
    if (!canManage) return;
    try {
      const data = await piCatalogApi.get();
      setProviders(data.providers || []);
    } catch {}
  }, [canManage]);

  useEffect(() => {
    void fetchEndpoints();
    void fetchCatalog();
  }, [fetchEndpoints, fetchCatalog]);

  // Poll active OAuth flows while one is in progress
  useEffect(() => {
    if (!activeOAuth) return;
    const timer = setInterval(async () => {
      try {
        const data = await piOAuthApi.poll(activeOAuth.provider);
        const flows = (data.flows || []) as PiOAuthFlow[];
        setOauthFlows(flows);
        const updated = flows.find((f) => f.provider === activeOAuth.provider);
        if (updated && updated.status === "approved") {
          setActiveOAuth(null);
          setShowAdd(false);
          setAddError(null);
          await fetchEndpoints();
        } else if (updated && (updated.status === "failed" || updated.status === "expired")) {
          setOauthError(updated.error || updated.status);
          setActiveOAuth(null);
        } else if (updated) {
          setActiveOAuth(updated);
        }
      } catch {}
    }, 5000);
    return () => clearInterval(timer);
  }, [activeOAuth, fetchEndpoints]);

  const providerMatches = providers.filter((p) =>
    p.id.toLowerCase().includes(providerQuery.toLowerCase()) ||
    p.display_name.toLowerCase().includes(providerQuery.toLowerCase())
  );
  const modelMatches = selectedProvider
    ? selectedProvider.models.filter(
        (m) =>
          m.id.toLowerCase().includes(modelQuery.toLowerCase()) ||
          (m.name || "").toLowerCase().includes(modelQuery.toLowerCase())
      )
    : [];

  const handleProviderSelect = (provider: PiCatalogProvider) => {
    setSelectedProvider(provider);
    setSelectedModel(null);
    setModelQuery("");
    setLoginMethod(provider.login_methods.includes("api_key") ? "api_key" : "oauth");
  };

  const handleAdd = async () => {
    if (!canManage || !selectedProvider || !selectedModel) {
      setAddError("Select a provider and model from the catalog.");
      return;
    }
    setAdding(true);
    setAddError(null);
    try {
      const autoId = endpointName.trim() || `${selectedProvider.id}-${selectedModel.id}`;
      await piEndpoints.add({
        endpoint_id: autoId,
        provider_kind: "openai_compat",
        base_url: selectedModel.baseUrl || "",
        model: selectedModel.id,
        pi_provider: selectedProvider.id,
        pi_model: selectedModel.id,
        keychain_service: `istara-pi-${selectedProvider.id}`,
        api_key: loginMethod === "api_key" ? apiKey.trim() : "",
      });
      setEndpointName("");
      setApiKey("");
      setSelectedProvider(null);
      setSelectedModel(null);
      setProviderQuery("");
      setModelQuery("");
      setShowAdd(false);
      await fetchEndpoints();
    } catch (err: any) {
      setAddError(err.message || "Failed to add endpoint");
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!canManage) return;
    try {
      await piEndpoints.delete(id);
      await fetchEndpoints();
    } catch (err: any) {
      window.dispatchEvent(
        new CustomEvent("istara:toast", {
          detail: { type: "error", title: "Delete Failed", message: err.message || "Failed to remove endpoint" },
        })
      );
    }
  };

  const handleOAuthStart = async (providerId: string) => {
    setOauthError(null);
    try {
      const res = await piOAuthApi.start(providerId);
      const flow = { provider: providerId, flow_type: res.flow_type, status: "pending", ...res };
      setActiveOAuth(flow);
    } catch (err: any) {
      setOauthError(err.message || "Failed to start OAuth login");
    }
  };

  if (!canManage) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
            <Server size={18} />
            Pi Model Management
          </h3>
          <Lock size={16} className="text-slate-400" aria-hidden="true" />
        </div>
        <p className="text-sm text-slate-500">
          Global admin access is required to manage cloud and API endpoints.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
          <Server size={18} />
          Pi Model Management
        </h3>
        <button
          onClick={() => setShowAdd((v) => !v)}
          className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-istara-600 text-white hover:bg-istara-700 transition-colors"
        >
          <Plus size={14} /> {showAdd ? "Cancel" : "Add Model"}
        </button>
      </div>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">
        All providers and models supported by Pi, with API-key or OAuth login — no manual endpoint
        typing needed. Select from the catalog or type to search and autocomplete.
      </p>
      {retirementNote && (
        <p className="text-xs text-slate-400 dark:text-slate-500 mb-3">{retirementNote}</p>
      )}

      {showAdd && (
        <div className="mb-4 p-3 rounded-lg border border-slate-200 dark:border-slate-700 space-y-3">
          {/* Step 1: provider (autocomplete) */}
          <div>
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">
              1. Provider
            </label>
            <input
              type="text"
              placeholder="Type to search providers (e.g. deepseek, openai, anthropic, google…)"
              value={providerQuery}
              onChange={(e) => { setProviderQuery(e.target.value); setSelectedProvider(null); }}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
              aria-label="Search Pi providers"
            />
            {providerQuery && !selectedProvider && (
              <ul className="mt-1 max-h-56 overflow-auto rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 divide-y divide-slate-100 dark:divide-slate-800">
                {providerMatches.map((provider) => (
                  <li key={provider.id}>
                    <button
                      type="button"
                      onClick={() => handleProviderSelect(provider)}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                    >
                      <span className="font-medium text-slate-900 dark:text-white">{provider.display_name}</span>
                      <span className="ml-2 text-xs text-slate-400 font-mono">{provider.id}</span>
                      <span className="ml-2 text-xs text-slate-400">({provider.models.length} models)</span>
                    </button>
                  </li>
                ))}
                {providerMatches.length === 0 && (
                  <li className="px-3 py-2 text-sm text-slate-400">No provider matches "{providerQuery}"</li>
                )}
              </ul>
            )}
            {selectedProvider && (
              <div className="mt-1 flex items-center gap-2 text-sm">
                <span className="font-medium text-istara-600 dark:text-istara-400">{selectedProvider.display_name}</span>
                <span className="text-xs text-slate-400 font-mono">{selectedProvider.id}</span>
                <button
                  type="button"
                  onClick={() => { setSelectedProvider(null); setProviderQuery(""); }}
                  className="text-xs text-slate-400 hover:text-slate-600"
                >
                  change
                </button>
              </div>
            )}
          </div>

          {/* Step 2: model (autocomplete) */}
          {selectedProvider && (
            <div>
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">
                2. Model ({selectedProvider.models.length} available)
              </label>
              <input
                type="text"
                placeholder="Type to search models (e.g. deepseek-v4-pro, gpt-5.4…)"
                value={modelQuery}
                onChange={(e) => { setModelQuery(e.target.value); setSelectedModel(null); }}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                aria-label="Search Pi models"
              />
              {modelQuery && !selectedModel && (
                <ul className="mt-1 max-h-56 overflow-auto rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 divide-y divide-slate-100 dark:divide-slate-800">
                  {modelMatches.slice(0, 50).map((model) => (
                    <li key={model.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedModel(model)}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                      >
                        <span className="font-medium text-slate-900 dark:text-white">{model.name || model.id}</span>
                        <span className="ml-2 text-xs text-slate-400 font-mono">{model.id}</span>
                        {model.contextWindow ? (
                          <span className="ml-2 text-xs text-slate-400">{(model.contextWindow / 1000).toFixed(0)}k ctx</span>
                        ) : null}
                        {model.reasoning ? (
                          <span className="ml-2 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded px-1.5 py-0.5">reasoning</span>
                        ) : null}
                      </button>
                    </li>
                  ))}
                  {modelMatches.length === 0 && (
                    <li className="px-3 py-2 text-sm text-slate-400">No model matches "{modelQuery}"</li>
                  )}
                </ul>
              )}
              {selectedModel && (
                <div className="mt-1 flex items-center gap-2 text-sm">
                  <span className="font-medium text-istara-600 dark:text-istara-400">{selectedModel.name || selectedModel.id}</span>
                  <span className="text-xs text-slate-400 font-mono">{selectedModel.id}</span>
                  <span className="text-xs text-slate-400">{selectedModel.contextWindow ? `${(selectedModel.contextWindow / 1000).toFixed(0)}k ctx` : ""}</span>
                  <button
                    type="button"
                    onClick={() => { setSelectedModel(null); setModelQuery(""); }}
                    className="text-xs text-slate-400 hover:text-slate-600"
                  >
                    change
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Step 3: login method */}
          {selectedProvider && selectedModel && (
            <div>
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">
                3. Login method
              </label>
              <div className="flex gap-2 flex-wrap">
                {selectedProvider.login_methods.includes("api_key") && (
                  <button
                    type="button"
                    onClick={() => setLoginMethod("api_key")}
                    className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                      loginMethod === "api_key"
                        ? "bg-istara-600 text-white border-istara-600"
                        : "border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                    }`}
                  >
                    API Key
                  </button>
                )}
                {selectedProvider.login_methods.includes("oauth") && (
                  <button
                    type="button"
                    onClick={() => setLoginMethod("oauth")}
                    className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                      loginMethod === "oauth"
                        ? "bg-istara-600 text-white border-istara-600"
                        : "border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                    }`}
                  >
                    {selectedProvider.oauth_flow === "pkce" ? "Sign in with OpenRouter" : "OAuth (subscription)"}
                  </button>
                )}
                {!selectedProvider.login_methods.includes("api_key") && !selectedProvider.login_methods.includes("oauth") && (
                  <span className="text-xs text-slate-400">No credential needed</span>
                )}
              </div>
              {loginMethod === "api_key" && (
                <div className="mt-2">
                  <input
                    type="password"
                    placeholder={`API key (${selectedProvider.env_var || "secret"}) — optional if set on the server`}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                    aria-label="API key"
                  />
                  <input
                    type="text"
                    placeholder="Endpoint name (optional; auto-generated if empty)"
                    value={endpointName}
                    onChange={(e) => setEndpointName(e.target.value)}
                    className="mt-2 w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                    aria-label="Endpoint name"
                  />
                </div>
              )}
              {loginMethod === "oauth" && !activeOAuth && (
                <div className="mt-2">
                  <button
                    type="button"
                    onClick={() => handleOAuthStart(selectedProvider.id)}
                    className="px-3 py-1.5 text-sm rounded-lg bg-istara-600 text-white hover:bg-istara-700 transition-colors"
                  >
                    Start {selectedProvider.display_name} login
                  </button>
                </div>
              )}
              {activeOAuth && (
                <div className="mt-2 p-3 rounded-lg border border-blue-200 dark:border-blue-900/40 bg-blue-50 dark:bg-blue-900/20">
                  <p className="text-sm text-slate-800 dark:text-slate-200">
                    Open <span className="font-mono text-blue-600 dark:text-blue-400">{activeOAuth.verification_uri}</span>
                    {activeOAuth.user_code ? <> and enter code <span className="font-mono font-semibold">{activeOAuth.user_code}</span></> : null}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Waiting for approval — the page updates automatically when you finish…
                  </p>
                  <button
                    type="button"
                    onClick={() => { void piOAuthApi.cancel(activeOAuth.provider); setActiveOAuth(null); }}
                    className="mt-2 text-xs text-slate-400 hover:text-slate-600"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Step 4: add */}
          {selectedProvider && selectedModel && loginMethod !== "oauth" && (
            <div className="flex gap-2">
              <button
                onClick={handleAdd}
                disabled={adding}
                className="px-3 py-1.5 text-sm rounded-lg bg-istara-600 text-white hover:bg-istara-700 transition-colors disabled:opacity-50"
              >
                {adding ? "Adding…" : "Add Model"}
              </button>
            </div>
          )}
          {oauthError && <p className="text-sm text-red-500">{oauthError}</p>}
          {addError && <p className="text-sm text-red-500">{addError}</p>}
        </div>
      )}

      {endpoints.length === 0 ? (
        <p className="text-sm text-slate-500">
          No configured models yet. The built-in <span className="font-mono">pi-deepseek-default</span> endpoint is always available.
        </p>
      ) : (
        <ul className="space-y-2">
          {endpoints.map((endpoint) => (
            <li
              key={endpoint.endpoint_id}
              className="flex items-center justify-between p-3 rounded-lg border border-slate-200 dark:border-slate-700"
            >
              <div>
                <p className="text-sm font-medium text-slate-900 dark:text-white">
                  {endpoint.endpoint_id}
                </p>
                <p className="text-xs text-slate-500">
                  {endpoint.model} · {endpoint.provider_kind} · {endpoint.base_url}
                </p>
              </div>
              <button
                onClick={() => handleDelete(endpoint.endpoint_id)}
                aria-label={`Delete ${endpoint.endpoint_id}`}
                className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
