"use client";

import { useCallback, useEffect, useState } from "react";
import { Cpu, HardDrive, Monitor, Wifi, WifiOff, RefreshCw, Server, Users, Gauge, Download } from "lucide-react";
import { settings as settingsApi, telemetry as telemetryApi } from "@/lib/api";
import type { HardwareInfo, ModelRecommendation } from "@/lib/types";
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
import AgenticCoreSection from "@/components/settings/AgenticCoreSection";
import PiModelManagement from "@/components/settings/PiModelManagement";
import { providerLabel } from "@/lib/modelProviders";

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

      {/* Agentic Core — first-class configuration, not a status-grid dropdown */}
      {canManageInfrastructure && models?.agentic_engine_default && (
        <AgenticCoreSection
          scope="global"
          value={models.agentic_engine_default === "pi" ? "pi" : "legacy"}
          canManage={canManageInfrastructure}
          onChange={async (engine) => {
            const result = await settingsApi.setAgenticEngine(engine === "pi" ? "pi" : "istara");
            setModels((current: any) => current ? { ...current, agentic_engine_default: result.agentic_engine_default === "pi" ? "pi" : "legacy" } : current);
          }}
        />
      )}

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
      {capabilities.canManageLlmInfrastructure && <PiModelManagement />}

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
