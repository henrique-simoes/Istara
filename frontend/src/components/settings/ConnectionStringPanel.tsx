"use client";

import { useState } from "react";
import { Copy, Check, Key, RefreshCw, Loader2, Shield } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ConnectionStringPanel() {
  const { user, teamMode } = useAuthStore();
  const isAdmin = user?.role === "admin";

  const [label, setLabel] = useState("");
  const [expiryHours, setExpiryHours] = useState(168);
  const [connectionString, setConnectionString] = useState("");
  const [generating, setGenerating] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Don't render for non-admins
  if (!isAdmin) return null;

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    setConnectionString("");
    try {
      const token = localStorage.getItem("reclaw_token");
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
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleRotateToken = async () => {
    if (!window.confirm("Rotate the network access token? All existing connection strings will be invalidated.")) return;
    setRotating(true);
    try {
      const token = localStorage.getItem("reclaw_token");
      await fetch(`${API_BASE}/api/connections/rotate-network-token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      setConnectionString("");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRotating(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(connectionString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <h3 className="font-medium text-slate-900 dark:text-white mb-3 flex items-center gap-2">
        <Key size={18} />
        Connection Strings
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        Generate a connection string to invite team members. They paste it into the login page
        or desktop app to connect their machine to this server.
      </p>

      {/* Generate form */}
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          placeholder="Label (e.g. Alice's laptop)"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
          aria-label="Connection string label"
        />
        <select
          value={expiryHours}
          onChange={(e) => setExpiryHours(Number(e.target.value))}
          className="px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
          aria-label="Connection string expiry"
        >
          <option value={24}>1 day</option>
          <option value={168}>7 days</option>
          <option value={720}>30 days</option>
          <option value={8760}>1 year</option>
        </select>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 transition-colors"
        >
          {generating ? <Loader2 size={14} className="animate-spin" /> : <Key size={14} />}
          Generate
        </button>
      </div>

      {/* Generated string */}
      {connectionString && (
        <div className="mb-3">
          <div className="flex items-center gap-2 p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700">
            <code className="flex-1 text-xs font-mono text-slate-700 dark:text-slate-300 break-all select-all">
              {connectionString}
            </code>
            <button
              onClick={handleCopy}
              className="shrink-0 p-2 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 transition-colors"
              aria-label="Copy connection string"
            >
              {copied ? <Check size={16} className="text-green-600" /> : <Copy size={16} />}
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Share this string with your team member. They paste it on the login page under "Join Server".
          </p>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-500 mb-3">{error}</p>
      )}

      {/* Security actions */}
      <div className="flex items-center gap-3 pt-2 border-t border-slate-200 dark:border-slate-700">
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
