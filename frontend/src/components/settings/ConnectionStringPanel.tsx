import { useEffect, useState, useCallback } from "react";
import { Copy, Check, Key, Loader2, Shield, Trash2, Clock } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useProjectStore } from "@/stores/projectStore";
import { cn, formatDate } from "@/lib/utils";

import { API_BASE, WS_BASE } from "@/lib/runtimeConfig";

interface ActiveConnectionString {
  id: string;
  label: string;
  connection_string_preview: string;
  token_type: "user_invite" | "compute_donation";
  intended_role?: string | null;
  expires_at: string;
  is_expired: boolean;
  is_active: boolean;
  is_redeemed: boolean;
  allowed_project_ids?: string[];
  redeemed_username?: string | null;
  redeemed_at?: string | null;
  last_validated_at?: string | null;
}

export default function ConnectionStringPanel() {
  const { user } = useAuthStore();
  const { projects, activeProjectId, fetchProjects } = useProjectStore();
  const isAdmin = user?.role === "admin";

  const [label, setLabel] = useState("");
  const [expiryHours, setExpiryHours] = useState(168);
  const [tokenType, setTokenType] = useState<"user_invite" | "compute_donation">("user_invite");
  const [role, setRole] = useState<"researcher" | "viewer" | "admin">("researcher");
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([]);
  const [connectionString, setConnectionString] = useState("");
  const [generatedTokenType, setGeneratedTokenType] = useState<"user_invite" | "compute_donation">("user_invite");
  const [activeStrings, setActiveStrings] = useState<ActiveConnectionString[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadActiveStrings = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("istara_token");
      const res = await fetch(`${API_BASE}/api/connections`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        const data = await res.json();
        setActiveStrings(data);
      }
    } catch (e) {
      console.error("Failed to load connection strings", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAdmin) loadActiveStrings();
  }, [isAdmin, loadActiveStrings]);

  useEffect(() => {
    if (isAdmin) void fetchProjects();
  }, [fetchProjects, isAdmin]);

  useEffect(() => {
    if (tokenType !== "compute_donation" || selectedProjectIds.length > 0) return;
    const defaultProjectId = activeProjectId || projects[0]?.id;
    if (defaultProjectId) setSelectedProjectIds([defaultProjectId]);
  }, [activeProjectId, projects, selectedProjectIds.length, tokenType]);

  const toggleSelectedProject = (projectId: string) => {
    setSelectedProjectIds((current) =>
      current.includes(projectId)
        ? current.filter((id) => id !== projectId)
        : [...current, projectId]
    );
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    setConnectionString("");
    try {
      const token = localStorage.getItem("istara_token");
      const serverUrl = window.location.origin;
      const endpoint = tokenType === "compute_donation"
        ? "/api/connections/compute-donation/generate"
        : "/api/connections/generate";
      if (tokenType === "compute_donation" && selectedProjectIds.length === 0) {
        throw new Error("Select at least one project for compute donation access");
      }
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          server_url: serverUrl,
          ws_url: `${WS_BASE}/ws/relay`,
          label: label.trim() || (tokenType === "compute_donation" ? "Compute Node" : "Team Member"),
          expires_hours: expiryHours,
          ...(tokenType === "user_invite" ? { role } : {}),
          ...(tokenType === "compute_donation"
            ? { allowed_project_ids: selectedProjectIds }
            : {}),
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Generation failed" }));
        throw new Error(data.detail || "Failed to generate");
      }
      const data = await res.json();
      setConnectionString(data.connection_string);
      setGeneratedTokenType(tokenType);
      setLabel("");
      loadActiveStrings();
      // Notify guided tour
      window.dispatchEvent(new CustomEvent("istara:connection-string-generated"));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleRevoke = async (id: string) => {
    if (!window.confirm("Revoke this connection string? Future attempts to redeem it will fail.")) return;
    try {
      const token = localStorage.getItem("istara_token");
      const res = await fetch(`${API_BASE}/api/connections/${id}`, {
        method: "DELETE",
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.ok) {
        loadActiveStrings();
      } else {
        const data = await res.json().catch(() => ({ detail: "Revocation failed" }));
        throw new Error(data.detail || "Revocation failed");
      }
    } catch (e: any) {
      setError(e.message || "Revocation failed");
    }
  };

  const handleRotateToken = async () => {
    if (!window.confirm("Rotate the network access token? All existing connection strings will be invalidated.")) return;
    setRotating(true);
    try {
      const token = localStorage.getItem("istara_token");
      const res = await fetch(`${API_BASE}/api/connections/rotate-network-token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Token rotation failed" }));
        throw new Error(data.detail || "Token rotation failed");
      }
      setConnectionString("");
      setGeneratedTokenType("user_invite");
      loadActiveStrings();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRotating(false);
    }
  };

  const handleCopy = async (str: string) => {
    try {
      await navigator.clipboard.writeText(str);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  if (!isAdmin) return null;

  return (
    <div id="tour-target-connection-strings" className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
          <Key size={18} />
          Connection Strings
        </h3>
        {loading && <Loader2 size={14} className="animate-spin text-slate-400" />}
      </div>

      {tokenType === "compute_donation" && (
        <div className="mb-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 p-3">
          <div className="mb-2 text-xs font-medium text-slate-700 dark:text-slate-200">
            Project access
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {projects.map((project) => (
              <label
                key={project.id}
                className="flex items-center gap-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1.5 text-xs text-slate-600 dark:text-slate-300"
              >
                <input
                  type="checkbox"
                  checked={selectedProjectIds.includes(project.id)}
                  onChange={() => toggleSelectedProject(project.id)}
                  className="h-3.5 w-3.5 rounded border-slate-300 text-istara-600 focus:ring-istara-500"
                />
                <span className="min-w-0 truncate">{project.name}</span>
              </label>
            ))}
          </div>
          {projects.length === 0 && (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Create a project before generating a compute donation string.
            </p>
          )}
        </div>
      )}
      <p className="text-sm text-slate-500 mb-4">
        Generate connection strings to invite team members or allow researchers to contribute local compute power to the network.
      </p>

      {/* Generate form */}
      <div className="grid grid-cols-1 gap-2 mb-4 md:grid-cols-[1fr_auto_auto_auto_auto]">
        <input
          type="text"
          placeholder={tokenType === "compute_donation" ? "Label (e.g. RTX Workstation)" : "Label (e.g. Researcher Laptop)"}
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-istara-500"
        />
        <select
          value={tokenType}
          onChange={(e) => setTokenType(e.target.value as "user_invite" | "compute_donation")}
          className="px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-istara-500"
        >
          <option value="user_invite">User invite</option>
          <option value="compute_donation">Compute donation</option>
        </select>
        {tokenType === "user_invite" && (
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as "researcher" | "viewer" | "admin")}
            className="px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-istara-500"
          >
            <option value="researcher">Researcher</option>
            <option value="viewer">Viewer</option>
            <option value="admin">Admin</option>
          </select>
        )}
        <select
          value={expiryHours}
          onChange={(e) => setExpiryHours(Number(e.target.value))}
          className="px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-istara-500"
        >
          <option value={24}>1 day</option>
          <option value={168}>7 days</option>
          <option value={720}>30 days</option>
          <option value={8760}>1 year</option>
        </select>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50 transition-colors"
        >
          {generating ? <Loader2 size={14} className="animate-spin" /> : <Key size={14} />}
          Generate
        </button>
      </div>

      {/* New: List of Active Strings */}
      {activeStrings.length > 0 && (
        <div className="mb-4 space-y-2 max-h-48 overflow-y-auto pr-1">
          {activeStrings.map((str) => (
            <div 
              key={str.id}
              className={cn(
                "flex items-center justify-between p-2 rounded-lg border text-xs transition-colors",
                str.is_expired 
                  ? "bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 opacity-60"
                  : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-istara-400"
              )}
            >
              <div className="flex flex-col gap-0.5 overflow-hidden">
                <span className="font-bold text-slate-700 dark:text-slate-200 truncate">{str.label}</span>
                <span className="font-mono text-[10px] text-slate-400 truncate">{str.connection_string_preview}</span>
                <div className="flex items-center gap-2 text-slate-400">
                  <span className="font-medium text-slate-500 dark:text-slate-300">
                    {str.token_type === "compute_donation" ? "Compute" : str.intended_role || "Invite"}
                  </span>
                  {str.token_type === "compute_donation" && (
                    <span>
                      {str.allowed_project_ids?.includes("*")
                        ? "All projects"
                        : `${str.allowed_project_ids?.length || 0} projects`}
                    </span>
                  )}
                  <span className="flex items-center gap-0.5"><Clock size={10} /> Exp: {formatDate(str.expires_at)}</span>
                  {str.is_redeemed && <span className="text-green-600 dark:text-green-400 font-medium">Redeemed</span>}
                  {!str.is_active && <span className="text-red-500 font-medium">Revoked</span>}
                  {str.is_expired && <span className="text-red-500 font-medium">Expired</span>}
                </div>
                {(str.redeemed_username || str.last_validated_at) && (
                  <div className="text-slate-400">
                    {str.redeemed_username
                      ? `User: ${str.redeemed_username}${str.redeemed_at ? ` on ${formatDate(str.redeemed_at)}` : ""}`
                      : `Last checked: ${formatDate(str.last_validated_at || "")}`}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleRevoke(str.id)}
                  className="p-1.5 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 text-slate-400 hover:text-red-600 transition-colors"
                  title="Revoke"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Generated string highlight (shown once on generation) */}
      {connectionString && (
        <div className="mb-4 p-3 bg-istara-50 dark:bg-istara-900/20 rounded-lg border border-istara-200 dark:border-istara-800 animate-in slide-in-from-top-2 duration-300">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-istara-600 dark:text-istara-400">New String Generated</span>
            <button onClick={() => setConnectionString("")} className="text-slate-400 hover:text-slate-600">×</button>
          </div>
          <div className="flex items-center gap-2 p-2 bg-white dark:bg-slate-900 rounded-md border border-istara-200 dark:border-istara-800">
            <code className="flex-1 text-[10px] font-mono text-slate-700 dark:text-slate-300 break-all select-all">
              {connectionString}
            </code>
            <button
              onClick={() => handleCopy(connectionString)}
              className="shrink-0 p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 transition-colors"
            >
              {copied ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
            </button>
          </div>
          <div className="mt-2 rounded-md border border-istara-200 dark:border-istara-800 bg-white/70 dark:bg-slate-900/60 p-2">
            {generatedTokenType === "compute_donation" ? (
              <>
                <div className="text-[10px] font-bold uppercase tracking-wider text-istara-600 dark:text-istara-400 mb-1">
                  Relay command
                </div>
                <code className="block text-[10px] font-mono text-slate-700 dark:text-slate-300 break-all select-all">
                  istara-relay --connection-string "{connectionString}"
                </code>
                <p className="mt-1.5 text-[11px] text-slate-500 dark:text-slate-400">
                  Without LM Studio, Ollama, or another supported local server, the relay connects idle and advertises models after one appears.
                </p>
              </>
            ) : (
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Team members paste this on the Sign In screen through Join Server.
              </p>
            )}
          </div>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-500 mb-4">{error}</p>
      )}

      {/* Security actions */}
      <div className="flex items-center gap-3 pt-3 border-t border-slate-200 dark:border-slate-700">
        <button
          onClick={handleRotateToken}
          disabled={rotating}
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-red-600 transition-colors"
          aria-label="Rotate network access token"
        >
          <Shield size={12} />
          {rotating ? "Rotating..." : "Rotate Network Token"}
        </button>
        <span className="text-xs text-slate-400">
          Invalidates all existing connection strings
        </span>
      </div>
    </div>
  );
}
