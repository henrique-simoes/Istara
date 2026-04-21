import { useEffect, useState, useCallback } from "react";
import { Copy, Check, Key, RefreshCw, Loader2, Shield, Trash2, Clock, Globe } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { cn, formatDate } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ActiveConnectionString {
  id: string;
  label: string;
  connection_string: string;
  expires_at: string;
  is_expired: boolean;
}

export default function ConnectionStringPanel() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === "admin";

  const [label, setLabel] = useState("");
  const [expiryHours, setExpiryHours] = useState(168);
  const [connectionString, setConnectionString] = useState("");
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

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    setConnectionString("");
    try {
      const token = localStorage.getItem("istara_token");
      const serverUrl = window.location.origin.replace(":3000", ":8000");
      const res = await fetch(`${API_BASE}/api/connections/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          server_url: serverUrl,
          label: label.trim() || "Team Member",
          expires_hours: expiryHours,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Generation failed" }));
        throw new Error(data.detail || "Failed to generate");
      }
      const data = await res.json();
      setConnectionString(data.connection_string);
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
      }
    } catch (e) {
      console.error("Revocation failed", e);
    }
  };

  const handleRotateToken = async () => {
    if (!window.confirm("Rotate the network access token? All existing connection strings will be invalidated.")) return;
    setRotating(true);
    try {
      const token = localStorage.getItem("istara_token");
      await fetch(`${API_BASE}/api/connections/rotate-network-token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      setConnectionString("");
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
      <p className="text-sm text-slate-500 mb-4">
        Generate connection strings to invite team members or allow researchers to contribute local compute power to the network.
      </p>

      {/* Generate form */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          placeholder="Label (e.g. Researcher Laptop)"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-istara-500"
        />
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
                <div className="flex items-center gap-2 text-slate-400">
                  <span className="flex items-center gap-0.5"><Clock size={10} /> Exp: {formatDate(str.expires_at)}</span>
                  {str.is_expired && <span className="text-red-500 font-medium">Expired</span>}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleCopy(str.connection_string)}
                  className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 transition-colors"
                  title="Copy string"
                >
                  <Copy size={14} />
                </button>
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
