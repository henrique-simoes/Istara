"use client";

import { useEffect, useState } from "react";
import { Download, CheckCircle2, AlertTriangle, Loader2, Shield, RefreshCw, Rocket } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UpdateInfo {
  update_available: boolean;
  current_version: string;
  latest_version: string;
  release_name?: string;
  published_at?: string;
  changelog?: string;
  release_url?: string;
  downloads?: Record<string, string>;
  error?: string;
}

/**
 * Update checker component for Settings page.
 * Checks GitHub Releases for newer versions.
 * Supports one-click auto-update (backup → git pull → rebuild → restart).
 */
export default function UpdateChecker() {
  const [checking, setChecking] = useState(false);
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
  const [updating, setUpdating] = useState(false);
  const [updateStatus, setUpdateStatus] = useState<"idle" | "backing_up" | "updating" | "restarting" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  // Auto-check on mount
  useEffect(() => {
    checkForUpdates();
  }, []);

  const getHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {};
    const token = localStorage.getItem("istara_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
  };

  const checkForUpdates = async () => {
    setChecking(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/updates/check`, { headers: getHeaders() });
      const data = await res.json();
      setUpdateInfo(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setChecking(false);
    }
  };

  const applyUpdate = async () => {
    setUpdating(true);
    setError(null);
    setUpdateStatus("backing_up");

    try {
      // The backend handles everything: backup → git pull → rebuild → restart
      setUpdateStatus("updating");
      const res = await fetch(`${API_BASE}/api/updates/apply`, {
        method: "POST",
        headers: { ...getHeaders(), "Content-Type": "application/json" },
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Update failed" }));
        throw new Error(data.detail);
      }

      setUpdateStatus("restarting");

      // The server will restart — poll until it comes back
      let attempts = 0;
      const maxAttempts = 60; // 3 minutes (every 3s)
      const pollInterval = setInterval(async () => {
        attempts++;
        try {
          const healthRes = await fetch(`${API_BASE}/api/updates/version`, {
            signal: AbortSignal.timeout(2000),
          });
          if (healthRes.ok) {
            const data = await healthRes.json();
            clearInterval(pollInterval);
            setUpdateStatus("done");
            setUpdateInfo((prev) =>
              prev ? { ...prev, current_version: data.version, update_available: false } : null,
            );
            // Reload after a brief pause to pick up new frontend code
            setTimeout(() => window.location.reload(), 2000);
          }
        } catch {
          // Server still restarting — keep polling
        }
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setUpdateStatus("error");
          setError("Server did not come back after 3 minutes. Check istara logs.");
        }
      }, 3000);
    } catch (e: any) {
      setError(e.message);
      setUpdateStatus("error");
    } finally {
      setUpdating(false);
    }
  };

  const statusMessages: Record<string, string> = {
    backing_up: "Creating backup...",
    updating: "Pulling latest code and rebuilding...",
    restarting: "Restarting server — please wait...",
    done: "Update complete! Reloading...",
    error: "Update failed",
  };

  return (
    <div id="tour-target-software-updates" className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
          <Download size={18} />
          Software Updates
        </h3>
        <button
          onClick={checkForUpdates}
          disabled={checking || updating}
          className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 flex items-center gap-1"
          aria-label="Check for updates"
        >
          {checking ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          {checking ? "Checking..." : "Check Now"}
        </button>
      </div>

      {/* Current version */}
      <div className="text-sm text-slate-500 mb-3">
        Current version: <span className="font-mono font-medium text-slate-700 dark:text-slate-300">{updateInfo?.current_version || "..."}</span>
      </div>

      {/* Update in progress */}
      {updateStatus !== "idle" && updateStatus !== "error" && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-4 mb-3">
          <div className="flex items-center gap-3">
            {updateStatus === "done" ? (
              <CheckCircle2 size={20} className="text-green-600 shrink-0" />
            ) : (
              <Loader2 size={20} className="text-amber-600 animate-spin shrink-0" />
            )}
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                {statusMessages[updateStatus]}
              </p>
              {updateStatus === "restarting" && (
                <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                  This usually takes 1-2 minutes. The page will reload automatically.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Update available */}
      {updateInfo?.update_available && updateStatus === "idle" && (
        <div className="rounded-lg border border-istara-200 dark:border-istara-800 bg-istara-50 dark:bg-istara-900/20 p-4 mb-3">
          <div className="flex items-start gap-3">
            <Rocket size={20} className="text-istara-600 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-istara-800 dark:text-istara-300">
                Istara {updateInfo.latest_version} is available
              </p>
              {updateInfo.release_name && (
                <p className="text-xs text-istara-600 dark:text-istara-400 mt-0.5">
                  {updateInfo.release_name}
                </p>
              )}
              {updateInfo.changelog && (
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-2 line-clamp-3">
                  {updateInfo.changelog}
                </p>
              )}

              <div className="flex items-center gap-3 mt-3">
                <button
                  onClick={applyUpdate}
                  disabled={updating}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-istara-600 text-white hover:bg-istara-700 disabled:opacity-50 transition-colors"
                >
                  <Shield size={14} />
                  Update Now
                </button>
                <p className="text-xs text-slate-400">
                  Auto-backup → update → restart
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* No update */}
      {updateInfo && !updateInfo.update_available && !updateInfo.error && updateStatus === "idle" && (
        <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
          <CheckCircle2 size={14} />
          You're running the latest version.
        </div>
      )}

      {/* Error */}
      {(updateInfo?.error || error) && (
        <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400 mt-2">
          <AlertTriangle size={12} />
          {error || updateInfo?.error}
        </div>
      )}
    </div>
  );
}
