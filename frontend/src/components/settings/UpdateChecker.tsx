"use client";

import { useEffect, useState } from "react";
import { Download, CheckCircle2, AlertTriangle, Loader2, ExternalLink, Shield } from "lucide-react";
import { cn } from "@/lib/utils";

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
 * Admins can trigger pre-update backup and download.
 */
export default function UpdateChecker() {
  const [checking, setChecking] = useState(false);
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [prepared, setPrepared] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-check on mount
  useEffect(() => {
    checkForUpdates();
  }, []);

  const checkForUpdates = async () => {
    setChecking(true);
    setError(null);
    try {
      const token = localStorage.getItem("reclaw_token");
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/updates/check`, { headers });
      const data = await res.json();
      setUpdateInfo(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setChecking(false);
    }
  };

  const prepareUpdate = async () => {
    setPreparing(true);
    setError(null);
    try {
      const token = localStorage.getItem("reclaw_token");
      const res = await fetch(`${API_BASE}/api/updates/prepare`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Backup failed" }));
        throw new Error(data.detail);
      }
      setPrepared(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setPreparing(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
          <Download size={18} />
          Software Updates
        </h3>
        <button
          onClick={checkForUpdates}
          disabled={checking}
          className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 flex items-center gap-1"
          aria-label="Check for updates"
        >
          {checking ? <Loader2 size={12} className="animate-spin" /> : null}
          {checking ? "Checking..." : "Check Now"}
        </button>
      </div>

      {/* Current version */}
      <div className="text-sm text-slate-500 mb-3">
        Current version: <span className="font-mono font-medium text-slate-700 dark:text-slate-300">{updateInfo?.current_version || "..."}</span>
      </div>

      {/* Update available */}
      {updateInfo?.update_available && (
        <div className="rounded-lg border border-reclaw-200 dark:border-reclaw-800 bg-reclaw-50 dark:bg-reclaw-900/20 p-4 mb-3">
          <div className="flex items-start gap-3">
            <Download size={20} className="text-reclaw-600 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-reclaw-800 dark:text-reclaw-300">
                Update Available: {updateInfo.latest_version}
              </p>
              {updateInfo.release_name && (
                <p className="text-xs text-reclaw-600 dark:text-reclaw-400 mt-0.5">
                  {updateInfo.release_name}
                </p>
              )}
              {updateInfo.changelog && (
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-2 line-clamp-3">
                  {updateInfo.changelog}
                </p>
              )}

              <div className="flex items-center gap-3 mt-3">
                {/* Step 1: Backup */}
                {!prepared ? (
                  <button
                    onClick={prepareUpdate}
                    disabled={preparing}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-reclaw-600 text-white hover:bg-reclaw-700 disabled:opacity-50 transition-colors"
                  >
                    {preparing ? <Loader2 size={12} className="animate-spin" /> : <Shield size={12} />}
                    {preparing ? "Creating backup..." : "Backup & Prepare Update"}
                  </button>
                ) : (
                  <>
                    <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                      <CheckCircle2 size={12} /> Backup complete
                    </span>
                    {/* Step 2: Download */}
                    {updateInfo.release_url && (
                      <a
                        href={updateInfo.release_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-reclaw-600 text-white hover:bg-reclaw-700 transition-colors"
                      >
                        <ExternalLink size={12} />
                        Download Update
                      </a>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* No update */}
      {updateInfo && !updateInfo.update_available && !updateInfo.error && (
        <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
          <CheckCircle2 size={14} />
          You're running the latest version.
        </div>
      )}

      {/* Error */}
      {(updateInfo?.error || error) && (
        <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
          <AlertTriangle size={12} />
          {updateInfo?.error || error}
        </div>
      )}
    </div>
  );
}
