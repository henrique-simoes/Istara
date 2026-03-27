"use client";

import { useEffect, useState } from "react";
import { Shield, Save, RefreshCw } from "lucide-react";
import { mcp as mcpApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { MCPAccessPolicy } from "@/lib/types";

const RISK_BADGE: Record<string, { label: string; classes: string }> = {
  low: { label: "LOW", classes: "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400" },
  sensitive: { label: "SENSITIVE", classes: "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400" },
  high: { label: "HIGH RISK", classes: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400" },
};

export default function MCPAccessPolicyEditor() {
  const [policy, setPolicy] = useState<MCPAccessPolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [localTools, setLocalTools] = useState<Record<string, { allowed: boolean; risk: "low" | "sensitive" | "high" }>>({});
  const [localResources, setLocalResources] = useState<Record<string, { allowed: boolean; risk: "low" | "sensitive" | "high" }>>({});
  const [maxFindings, setMaxFindings] = useState(100);
  const [maxSkillExec, setMaxSkillExec] = useState(10);

  useEffect(() => {
    mcpApi.server.policy()
      .then((data) => {
        setPolicy(data);
        setLocalTools(data.tools || {});
        setLocalResources(data.resources || {});
        setMaxFindings(data.limits?.max_findings_per_request || 100);
        setMaxSkillExec(data.limits?.max_skill_executions_per_hour || 10);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const toggleTool = (toolName: string) => {
    setLocalTools((prev) => ({
      ...prev,
      [toolName]: { ...prev[toolName], allowed: !prev[toolName]?.allowed },
    }));
    setSaved(false);
  };

  const toggleResource = (resName: string) => {
    setLocalResources((prev) => ({
      ...prev,
      [resName]: { ...prev[resName], allowed: !prev[resName]?.allowed },
    }));
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await mcpApi.server.updatePolicy({
        tools: localTools,
        resources: localResources,
        limits: {
          max_findings_per_request: maxFindings,
          max_skill_executions_per_hour: maxSkillExec,
        },
      });
      setSaved(true);
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-14 rounded-lg bg-slate-100 dark:bg-slate-800 animate-pulse" />
        ))}
      </div>
    );
  }

  const toolEntries = Object.entries(localTools);
  const resourceEntries = Object.entries(localResources);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield size={18} className="text-reclaw-500" />
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Access Policy</h2>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 transition-colors"
        >
          {saving ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
          {saved ? "Saved!" : "Save Policy"}
        </button>
      </div>

      {/* Tools */}
      <div>
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Tool Access</h3>
        {toolEntries.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">No tools configured in policy.</p>
        ) : (
          <div className="space-y-2">
            {toolEntries.map(([name, config]) => {
              const riskBadge = RISK_BADGE[config.risk] || RISK_BADGE.low;
              return (
                <div key={name} className="flex items-center justify-between p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => toggleTool(name)}
                      role="switch"
                      aria-checked={config.allowed}
                      aria-label={`Toggle ${name}`}
                      className={cn(
                        "w-9 h-5 rounded-full transition-colors relative",
                        config.allowed ? "bg-reclaw-500" : "bg-slate-300 dark:bg-slate-600"
                      )}
                    >
                      <span className={cn(
                        "block w-3.5 h-3.5 rounded-full bg-white absolute top-0.5 transition-transform",
                        config.allowed ? "translate-x-4" : "translate-x-0.5"
                      )} />
                    </button>
                    <span className="text-sm text-slate-900 dark:text-white font-mono">{name}</span>
                  </div>
                  <span className={cn("text-[10px] px-2 py-0.5 rounded-full font-bold", riskBadge.classes)}>
                    {riskBadge.label}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Resources */}
      <div>
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Resource Access</h3>
        {resourceEntries.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">No resources configured in policy.</p>
        ) : (
          <div className="space-y-2">
            {resourceEntries.map(([name, config]) => {
              const riskBadge = RISK_BADGE[config.risk] || RISK_BADGE.low;
              return (
                <div key={name} className="flex items-center justify-between p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => toggleResource(name)}
                      role="switch"
                      aria-checked={config.allowed}
                      aria-label={`Toggle ${name}`}
                      className={cn(
                        "w-9 h-5 rounded-full transition-colors relative",
                        config.allowed ? "bg-reclaw-500" : "bg-slate-300 dark:bg-slate-600"
                      )}
                    >
                      <span className={cn(
                        "block w-3.5 h-3.5 rounded-full bg-white absolute top-0.5 transition-transform",
                        config.allowed ? "translate-x-4" : "translate-x-0.5"
                      )} />
                    </button>
                    <span className="text-sm text-slate-900 dark:text-white font-mono">{name}</span>
                  </div>
                  <span className={cn("text-[10px] px-2 py-0.5 rounded-full font-bold", riskBadge.classes)}>
                    {riskBadge.label}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Rate Limits */}
      <div>
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Rate Limits</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
              Max Findings per Request
            </label>
            <input
              type="number"
              min={1}
              value={maxFindings}
              onChange={(e) => { setMaxFindings(parseInt(e.target.value) || 1); setSaved(false); }}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
              Max Skill Executions per Hour
            </label>
            <input
              type="number"
              min={1}
              value={maxSkillExec}
              onChange={(e) => { setMaxSkillExec(parseInt(e.target.value) || 1); setSaved(false); }}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
