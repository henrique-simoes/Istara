"use client";

import { useEffect, useState } from "react";
import { Cpu, HardDrive, Monitor, Wifi, WifiOff, RefreshCw } from "lucide-react";
import { settings as settingsApi } from "@/lib/api";
import type { HardwareInfo, ModelRecommendation } from "@/lib/types";

export default function SettingsView() {
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [recommendation, setRecommendation] = useState<ModelRecommendation | null>(null);
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [models, setModels] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [hw, status, mdl] = await Promise.all([
        settingsApi.hardware(),
        settingsApi.status(),
        settingsApi.models(),
      ]);
      setHardware(hw.hardware);
      setRecommendation(hw.recommendation);
      setSystemStatus(status);
      setModels(mdl);
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

      {/* System Status */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
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
            <span className="text-sm text-slate-500">Ollama:</span>
            {systemStatus?.services?.ollama === "connected" ? (
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
            <span className="text-sm text-slate-500">Model:</span>
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
            Hardware
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
              <p className="text-slate-500">Available for ReClaw</p>
              <p className="font-medium text-reclaw-600">{hardware.reclaw_ram_budget_gb} GB</p>
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
        <div className="bg-reclaw-50 dark:bg-reclaw-900/20 rounded-xl border border-reclaw-200 dark:border-reclaw-800 p-5">
          <h3 className="font-medium text-reclaw-800 dark:text-reclaw-300 mb-3 flex items-center gap-2">
            <HardDrive size={18} />
            Recommended Model
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-reclaw-600 dark:text-reclaw-400">Model</p>
              <p className="font-bold font-mono text-reclaw-800 dark:text-reclaw-200">
                {recommendation.model_name}
              </p>
            </div>
            <div>
              <p className="text-reclaw-600 dark:text-reclaw-400">Quantization</p>
              <p className="font-medium font-mono">{recommendation.quantization}</p>
            </div>
            <div>
              <p className="text-reclaw-600 dark:text-reclaw-400">Context Length</p>
              <p className="font-medium">{recommendation.context_length.toLocaleString()} tokens</p>
            </div>
            <div>
              <p className="text-reclaw-600 dark:text-reclaw-400">GPU Layers</p>
              <p className="font-medium">
                {recommendation.gpu_layers === -1 ? "All (full offload)" : recommendation.gpu_layers}
              </p>
            </div>
          </div>
          <p className="mt-3 text-xs text-reclaw-600 dark:text-reclaw-400 italic">
            {recommendation.reason}
          </p>
        </div>
      )}

      {/* Available Models */}
      {models?.models && models.models.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="font-medium text-slate-900 dark:text-white mb-3">Available Models</h3>
          <div className="space-y-2">
            {models.models.map((model: any) => (
              <div
                key={model.name}
                className="flex items-center justify-between py-2 px-3 rounded-lg bg-slate-50 dark:bg-slate-900"
              >
                <div>
                  <p className="text-sm font-mono font-medium text-slate-900 dark:text-white">
                    {model.name}
                  </p>
                  {model.size && (
                    <p className="text-xs text-slate-400">
                      {(model.size / 1e9).toFixed(1)} GB
                    </p>
                  )}
                </div>
                {model.name === models.active_model && (
                  <span className="text-xs bg-reclaw-100 dark:bg-reclaw-900/30 text-reclaw-700 dark:text-reclaw-400 rounded-full px-2 py-0.5">
                    Active
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={fetchAll}
        className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
      >
        <RefreshCw size={14} />
        Refresh
      </button>
    </div>
  );
}
