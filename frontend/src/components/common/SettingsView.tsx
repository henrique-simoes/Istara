"use client";

import { useEffect, useState } from "react";
import { Cpu, HardDrive, Monitor, Wifi, WifiOff, RefreshCw, Plus, Server, Trash2, Users, Lock, Gauge, Download, ToggleLeft, ToggleRight } from "lucide-react";
import { settings as settingsApi, llmServers, telemetry as telemetryApi } from "@/lib/api";
import type { HardwareInfo, ModelRecommendation } from "@/lib/types";
import { useAuthStore } from "@/stores/authStore";
import UserManagement from "./UserManagement";
import ConnectionStringPanel from "@/components/settings/ConnectionStringPanel";
import UpdateChecker from "@/components/settings/UpdateChecker";
import DonateComputeToggle from "@/components/common/DonateComputeToggle";
import PasskeyManager from "@/components/settings/PasskeyManager";
import TOTPManager from "@/components/settings/TOTPManager";
import { resetAllOnboarding } from "@/hooks/useViewOnboarding";

export default function SettingsView() {
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [recommendation, setRecommendation] = useState<ModelRecommendation | null>(null);
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [models, setModels] = useState<any>(null);
  const [servers, setServers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [hw, status, mdl, srv] = await Promise.all([
        settingsApi.hardware(),
        settingsApi.status(),
        settingsApi.models(),
        llmServers.list().catch(() => ({ servers: [] })),
      ]);
      setHardware(hw.hardware);
      setRecommendation(hw.recommendation);
      setSystemStatus(status);
      setModels(mdl);
      setServers(srv.servers || []);
    } catch (e) {
      console.error("Failed to load settings:", e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchAll();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <RefreshCw size={20} className="animate-spin mr-2" />
        Loading system info...
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto space-y-6">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-white">⚙️ Settings</h2>

      {/* Software Updates */}
      <UpdateChecker />

      {/* Team Members */}
      <div id="tour-target-user-management">
        <UserManagement />
      </div>

      {/* Connection Strings (admin only, team mode) */}
      <ConnectionStringPanel />

      {/* Compute Donation */}
      <DonateComputeToggle />

      {/* Passkey Management */}
      <PasskeyManager />

      {/* Two-Factor Authentication */}
      <TOTPManager />

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
              LLM ({systemStatus?.provider || "unknown"}):
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
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">Server Model:</span>
            <span className="text-sm font-mono">{systemStatus?.config?.model || "—"}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-500">Embed Model:</span>
            <span className="text-sm font-mono">{systemStatus?.config?.embed_model || "—"}</span>
          </div>
        </div>
      </div>

      {/* Hardware */}
      {hardware && (
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
              <p className="font-medium text-slate-900 dark:text-white">{hardware.total_ram_gb} GB</p>
            </div>
            <div>
              <p className="text-slate-500">Available for Istara</p>
              <p className="font-medium text-istara-600">{hardware.istara_ram_budget_gb} GB</p>
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
      {recommendation && (
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
      {models?.models && models.models.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="font-medium text-slate-900 dark:text-white mb-3">Available Models</h3>
          <div className="space-y-2">
            {models.models.map((model: any) => {
              const providerLabel =
                model.provider_type === "ollama"
                  ? "Ollama"
                  : model.provider_type === "lmstudio"
                  ? "LM Studio"
                  : model.provider_type === "openai_compat"
                  ? "OpenAI Compatible"
                  : model.provider_type || "Unknown";
              return (
                <div
                  key={`${model.name}-${model.server_name || ""}`}
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
                        {providerLabel}
                      </span>
                    </div>
                  </div>
                  {model.name === models.active_model ? (
                    <span className="text-xs bg-istara-100 dark:bg-istara-900/30 text-istara-700 dark:text-istara-400 rounded-full px-2 py-0.5 ml-2 shrink-0">
                      Active
                    </span>
                  ) : (
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
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Pull new model */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <h3 className="font-medium text-slate-900 dark:text-white mb-2">Pull New Model</h3>
        <p className="text-xs text-slate-500 mb-3">
          {systemStatus?.provider === "lmstudio"
            ? "Load models through LM Studio's UI, or enter a model name to switch."
            : "Download a new model from the Ollama registry."}
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

      {/* LLM Servers */}
      <LLMServersSection />

      {/* Telemetry (Local-first, No phone-home) */}
      <TelemetrySection />

      {/* Team Mode */}
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
                const token = localStorage.getItem("istara_token");
                const headers: Record<string, string> = { "Content-Type": "application/json" };
                if (token) headers["Authorization"] = `Bearer ${token}`;
                await fetch(
                  `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/settings/team-mode`,
                  { method: "POST", headers, body: JSON.stringify({ enabled: newState }) }
                );
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

function LLMServersSection() {
  const [servers, setServers] = useState<any[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newHost, setNewHost] = useState("");
  const [newType, setNewType] = useState("openai_compat");
  const [newApiKey, setNewApiKey] = useState("");
  const [addError, setAddError] = useState<string | null>(null);

  const fetchServers = async () => {
    try {
      const data = await llmServers.list();
      setServers(data.servers || []);
    } catch {}
  };

  useEffect(() => {
    fetchServers();
  }, []);

  const handleAdd = async () => {
    if (!newName.trim() || !newHost.trim()) return;
    setAddError(null);
    try {
      const result = await llmServers.add({
        name: newName.trim(),
        provider_type: newType,
        host: newHost.trim(),
        api_key: newApiKey.trim() || undefined,
      });
      setNewName("");
      setNewHost("");
      setNewApiKey("");
      setShowAdd(false);
      await fetchServers();
      // If the server was added but is unhealthy, show a toast with guidance
      if (result && !result.is_healthy) {
        window.dispatchEvent(
          new CustomEvent("istara:toast", {
            detail: {
              type: "warning",
              title: "Server Unreachable",
              message: `${newName.trim()} was added but could not connect. Check the host URL and API key.`,
            },
          })
        );
      }
    } catch (err: any) {
      setAddError(err.message || "Failed to add server");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await llmServers.delete(id);
      await fetchServers();
    } catch (err: any) {
      window.dispatchEvent(
        new CustomEvent("istara:toast", {
          detail: {
            type: "error",
            title: "Delete Failed",
            message: err.message || "Failed to remove server",
          },
        })
      );
    }
  };

  const handleHealthCheck = async (id: string) => {
    try {
      await llmServers.healthCheck(id);
      await fetchServers();
    } catch (err: any) {
      window.dispatchEvent(
        new CustomEvent("istara:toast", {
          detail: {
            type: "error",
            title: "Health Check Failed",
            message: err.message || "Could not reach server",
          },
        })
      );
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
          <Server size={18} />
          LLM Servers
        </h3>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500"
          aria-label="Add LLM server"
        >
          <Plus size={16} />
        </button>
      </div>

      <p className="text-xs text-slate-500 mb-3">
        Connect to any Ollama, LM Studio, or OpenAI-compatible LLM server.
      </p>

      {showAdd && (
        <div className="mb-3 p-3 bg-slate-50 dark:bg-slate-900 rounded-lg space-y-2">
          <input
            type="text"
            placeholder="Server name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="w-full px-2 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
          />
          <input
            type="text"
            placeholder="Host URL (e.g. http://192.168.1.100:1234)"
            value={newHost}
            onChange={(e) => setNewHost(e.target.value)}
            className="w-full px-2 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
          />
          <select
            value={newType}
            onChange={(e) => setNewType(e.target.value)}
            className="w-full px-2 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
            aria-label="Provider type"
          >
            <option value="openai_compat">OpenAI Compatible</option>
            <option value="lmstudio">LM Studio</option>
            <option value="ollama">Ollama</option>
          </select>
          <input
            type="password"
            placeholder="API key (leave blank if server has no auth)"
            value={newApiKey}
            onChange={(e) => setNewApiKey(e.target.value)}
            className="w-full px-2 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
            aria-label="API key"
          />
          {addError && (
            <p className="text-xs text-red-500">{addError}</p>
          )}
          <button
            onClick={handleAdd}
            className="w-full py-1.5 bg-istara-600 hover:bg-istara-700 text-white text-sm font-medium rounded"
          >
            Add Server
          </button>
        </div>
      )}

      {servers.length > 0 ? (
        <div className="space-y-2">
          {servers.map((s) => (
            <div key={s.id} className="flex items-center gap-2 p-2 rounded border border-slate-100 dark:border-slate-700">
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${s.is_healthy ? "bg-green-500" : "bg-red-500"}`} title={s.is_healthy ? "Connected" : (s.health_error || "Unreachable")} />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-800 dark:text-slate-200 flex items-center gap-1">
                  {s.name}
                  {s.has_api_key && <span title="API key configured"><Lock size={10} className="text-slate-400" /></span>}
                </div>
                <div className="text-xs text-slate-400 truncate">{s.host} ({s.provider_type})</div>
                {!s.is_healthy && s.health_error && (
                  <div className="text-xs text-red-500 mt-0.5 truncate" title={s.health_error}>{s.health_error.length > 60 ? s.health_error.slice(0, 60) + "…" : s.health_error}</div>
                )}
              </div>
              <button
                onClick={() => handleHealthCheck(s.id)}
                className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400"
                aria-label="Check health"
                title="Health check"
              >
                <RefreshCw size={12} />
              </button>
              <button
                onClick={() => handleDelete(s.id)}
                className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-slate-400 hover:text-red-500"
                aria-label="Remove server"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-400">
          No external servers. Local Ollama/LM Studio detected automatically.
        </p>
      )}
    </div>
  );
}
