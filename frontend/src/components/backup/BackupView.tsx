"use client";

import { useEffect, useState, useRef } from "react";
import {
  Archive,
  Download,
  RotateCcw,
  Shield,
  Trash2,
  RefreshCw,
  Clock,
  HardDrive,
  ChevronDown,
  ChevronUp,
  Plus,
  Upload,
} from "lucide-react";
import { backups as backupsApi } from "@/lib/api";
import type { BackupRecord, BackupConfig } from "@/lib/types";
import { cn } from "@/lib/utils";
import ViewOnboarding from "@/components/common/ViewOnboarding";

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1);
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return "unknown";
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  verified: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  in_progress: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
};

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function boundedNumber(value: string, fallback: number, min: number, max: number): number {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

export default function BackupView() {
  const [backupList, setBackupList] = useState<BackupRecord[]>([]);
  const [config, setConfig] = useState<BackupConfig | null>(null);
  const [estimate, setEstimate] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [configForm, setConfigForm] = useState<Partial<BackupConfig>>({});
  const [savingConfig, setSavingConfig] = useState(false);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [list, cfg] = await Promise.all([
        backupsApi.list(),
        backupsApi.config(),
      ]);
      const backupArr = Array.isArray(list) ? list : (list as any)?.backups || [];
      setBackupList(backupArr);
      setConfig(cfg);
      setConfigForm(cfg);
    } catch (e) {
      setError(errorMessage(e, "Failed to load backup data."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleCreate = async (type: "full" | "incremental") => {
    setCreating(true);
    setError(null);
    setNotice(null);
    try {
      await backupsApi.create(type);
      await fetchAll();
      setNotice(`${type === "full" ? "Full" : "Incremental"} backup created.`);
    } catch (e) {
      setError(errorMessage(e, "Failed to create backup."));
    } finally {
      setCreating(false);
    }
  };

  const handleEstimate = async () => {
    setError(null);
    try {
      const est = await backupsApi.estimate();
      setEstimate(est);
    } catch (e) {
      setError(errorMessage(e, "Failed to estimate backup size."));
    }
  };

  const handleRestore = async (id: string) => {
    if (!window.confirm("Restore from this backup? All current data will be overwritten.")) return;
    setActionLoading((prev) => ({ ...prev, [`restore-${id}`]: true }));
    setError(null);
    setNotice(null);
    try {
      await backupsApi.restore(id);
      setNotice("Restore completed. Reloading the app...");
      setTimeout(() => window.location.reload(), 1500);
    } catch (e) {
      setError(errorMessage(e, "Failed to restore backup."));
    } finally {
      setActionLoading((prev) => ({ ...prev, [`restore-${id}`]: false }));
    }
  };

  const handleUploadAndRestore = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!window.confirm("Upload and restore from this backup file? All current data will be overwritten.")) {
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setRestoring(true);
    setError(null);
    setNotice(null);
    try {
      await backupsApi.uploadRestore(file);
      setNotice("Uploaded backup restored. Reloading the app...");
      setTimeout(() => window.location.reload(), 1500);
    } catch (err) {
      setError(errorMessage(err, "Restore failed. Check server logs."));
    } finally {
      setRestoring(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleVerify = async (id: string) => {
    setActionLoading((prev) => ({ ...prev, [`verify-${id}`]: true }));
    setError(null);
    setNotice(null);
    try {
      await backupsApi.verify(id);
      await fetchAll();
      setNotice("Backup verified.");
    } catch (e) {
      setError(errorMessage(e, "Failed to verify backup."));
    } finally {
      setActionLoading((prev) => ({ ...prev, [`verify-${id}`]: false }));
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Delete this backup archive? This cannot be undone.")) return;
    setActionLoading((prev) => ({ ...prev, [`delete-${id}`]: true }));
    setError(null);
    setNotice(null);
    try {
      await backupsApi.remove(id);
      setBackupList((prev) => prev.filter((b) => b.id !== id));
      setNotice("Backup deleted.");
    } catch (e) {
      setError(errorMessage(e, "Failed to delete backup."));
    } finally {
      setActionLoading((prev) => ({ ...prev, [`delete-${id}`]: false }));
    }
  };

  const handleDownload = async (backup: BackupRecord) => {
    setActionLoading((prev) => ({ ...prev, [`download-${backup.id}`]: true }));
    setError(null);
    try {
      const blob = await backupsApi.download(backup.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = backup.filename || `istara_backup_${backup.id}.tar.gz`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(errorMessage(e, "Failed to download backup."));
    } finally {
      setActionLoading((prev) => ({ ...prev, [`download-${backup.id}`]: false }));
    }
  };

  const handleSaveConfig = async () => {
    setSavingConfig(true);
    setError(null);
    setNotice(null);
    try {
      await backupsApi.updateConfig(configForm);
      const cfg = await backupsApi.config();
      setConfig(cfg);
      setConfigForm(cfg);
      setNotice("Backup configuration saved.");
    } catch (e) {
      setError(errorMessage(e, "Failed to save configuration."));
    } finally {
      setSavingConfig(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <RefreshCw size={20} className="animate-spin mr-2" />
        Loading backup data...
      </div>
    );
  }

  const totalStorage = backupList.reduce((sum, b) => sum + (b.size_bytes || 0), 0);
  const lastBackup = backupList.length > 0 ? backupList[0] : null;

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto space-y-6">
      <ViewOnboarding viewId="backup" title="Data Protection" description="Create and restore backups of your entire Istara instance — database, files, vector store, and settings." chatPrompt="How do I backup my data?" />
      {/* Header */}
      <div className="flex items-center gap-3">
        <Archive size={24} className="text-istara-600 dark:text-istara-400" />
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          Backup & Recovery
        </h2>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}
      {notice && (
        <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-900/50 dark:bg-green-900/20 dark:text-green-300">
          {notice}
        </div>
      )}

      {/* Status Card */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Last Backup</div>
            <div className="text-sm font-medium text-slate-900 dark:text-white">
              {lastBackup ? timeAgo(lastBackup.created_at) : "Never"}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Next Scheduled</div>
            <div className="text-sm font-medium text-slate-900 dark:text-white">
              {config?.backup_enabled && lastBackup
                ? `in ${config.backup_interval_hours}h`
                : "Not scheduled"}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Total Storage</div>
            <div className="text-sm font-medium text-slate-900 dark:text-white flex items-center gap-1">
              <HardDrive size={14} />
              {formatBytes(totalStorage)}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Backup Count</div>
            <div className="text-sm font-medium text-slate-900 dark:text-white">
              {backupList.length}
            </div>
          </div>
        </div>
      </div>

      {/* Actions Row */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => handleCreate("full")}
          disabled={creating}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
            "bg-istara-600 text-white hover:bg-istara-700 disabled:opacity-50"
          )}
        >
          {creating ? <RefreshCw size={16} className="animate-spin" /> : <Plus size={16} />}
          Create Full Backup
        </button>
        <button
          onClick={() => handleCreate("incremental")}
          disabled={creating}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
            "border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300",
            "hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50"
          )}
        >
          Create Incremental
        </button>
        <button
          onClick={handleEstimate}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
            "border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300",
            "hover:bg-slate-100 dark:hover:bg-slate-800"
          )}
        >
          <HardDrive size={16} />
          Estimate Size
        </button>

        <input
          type="file"
          ref={fileInputRef}
          onChange={handleUploadAndRestore}
          accept=".tar.gz"
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={restoring}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
            "border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300",
            "hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50"
          )}
        >
          {restoring ? <RefreshCw size={16} className="animate-spin" /> : <Upload size={16} />}
          Restore from File
        </button>
      </div>

      {/* Estimate Result */}
      {estimate && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 text-sm text-blue-700 dark:text-blue-300">
          Estimated backup size: <strong>{formatBytes(estimate.size_bytes || estimate.compressed_estimate_bytes || 0)}</strong>
          {estimate.components && (
            <span className="ml-2 text-blue-500">
              ({Object.keys(estimate.components).length} components)
            </span>
          )}
        </div>
      )}

      {/* Backup List */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-700">
          <h3 className="font-medium text-slate-900 dark:text-white text-sm">Backup History</h3>
        </div>

        {backupList.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            No backups yet. Create your first backup to get started.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 text-left">
                  <th className="px-4 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Date</th>
                  <th className="px-4 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Type</th>
                  <th className="px-4 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Size</th>
                  <th className="px-4 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Status</th>
                  <th className="px-4 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {backupList.map((backup) => (
                  <tr
                    key={backup.id}
                    className="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30"
                  >
                    <td className="px-4 py-3 text-slate-900 dark:text-slate-200 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <Clock size={14} className="text-slate-400" />
                        {timeAgo(backup.created_at)}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">{backup.filename}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "inline-flex px-2 py-0.5 rounded-full text-xs font-medium",
                          backup.backup_type === "full"
                            ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                            : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        )}
                      >
                        {backup.backup_type === "full" ? "Full" : "Incremental"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300 whitespace-nowrap">
                      {formatBytes(backup.size_bytes)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "inline-flex px-2 py-0.5 rounded-full text-xs font-medium",
                          STATUS_COLORS[backup.status] || STATUS_COLORS.completed
                        )}
                      >
                        {backup.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleRestore(backup.id)}
                          disabled={!!actionLoading[`restore-${backup.id}`]}
                          title="Restore"
                          className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-blue-600 transition-colors disabled:opacity-50"
                        >
                          <RotateCcw size={14} />
                        </button>
                        <button
                          onClick={() => handleVerify(backup.id)}
                          disabled={!!actionLoading[`verify-${backup.id}`]}
                          title="Verify"
                          className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-green-600 transition-colors disabled:opacity-50"
                        >
                          <Shield size={14} />
                        </button>
                        <button
                          onClick={() => handleDelete(backup.id)}
                          disabled={!!actionLoading[`delete-${backup.id}`]}
                          title="Delete"
                          className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-red-600 transition-colors disabled:opacity-50"
                        >
                          <Trash2 size={14} />
                        </button>
                        <button
                          onClick={() => handleDownload(backup)}
                          disabled={!!actionLoading[`download-${backup.id}`]}
                          title="Download"
                          className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-purple-600 transition-colors disabled:opacity-50"
                        >
                          <Download size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Configuration Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setShowConfig(!showConfig)}
          className="w-full flex items-center justify-between px-5 py-3 text-sm font-medium text-slate-900 dark:text-white hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors rounded-xl"
        >
          <span className="flex items-center gap-2">
            <RefreshCw size={16} />
            Backup Configuration
          </span>
          {showConfig ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {showConfig && config && (
          <div className="px-5 pb-5 space-y-4 border-t border-slate-200 dark:border-slate-700 pt-4">
            {/* Toggle: Automatic backups */}
            <div className="flex items-center justify-between">
              <label className="text-sm text-slate-700 dark:text-slate-300">
                Automatic backups enabled
              </label>
              <button
                onClick={() =>
                  setConfigForm((prev) => ({
                    ...prev,
                    backup_enabled: !prev.backup_enabled,
                  }))
                }
                className={cn(
                  "relative w-10 h-5 rounded-full transition-colors",
                  configForm.backup_enabled
                    ? "bg-istara-600"
                    : "bg-slate-300 dark:bg-slate-600"
                )}
              >
                <span
                  className={cn(
                    "absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform",
                    configForm.backup_enabled && "translate-x-5"
                  )}
                />
              </button>
            </div>

            {/* Backup interval */}
            <div className="flex items-center justify-between">
              <label className="text-sm text-slate-700 dark:text-slate-300">
                Backup interval (hours)
              </label>
              <input
                type="number"
                min={1}
                max={168}
                value={configForm.backup_interval_hours || 24}
                onChange={(e) =>
	                  setConfigForm((prev) => ({
	                    ...prev,
	                    backup_interval_hours: boundedNumber(e.target.value, 24, 1, 168),
	                  }))
                }
                className="w-20 px-2 py-1 text-sm rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-istara-500"
              />
            </div>

            {/* Retention count */}
            <div className="flex items-center justify-between">
              <label className="text-sm text-slate-700 dark:text-slate-300">
                Retention count
              </label>
              <input
                type="number"
                min={1}
                max={100}
                value={configForm.backup_retention_count || 10}
                onChange={(e) =>
	                  setConfigForm((prev) => ({
	                    ...prev,
	                    backup_retention_count: boundedNumber(e.target.value, 10, 1, 100),
	                  }))
                }
                className="w-20 px-2 py-1 text-sm rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-istara-500"
              />
            </div>

            {/* Full backup frequency */}
            <div className="flex items-center justify-between">
              <label className="text-sm text-slate-700 dark:text-slate-300">
                Full backup frequency (days)
              </label>
              <input
                type="number"
                min={1}
	                max={365}
                value={configForm.backup_full_interval_days || 7}
                onChange={(e) =>
	                  setConfigForm((prev) => ({
	                    ...prev,
	                    backup_full_interval_days: boundedNumber(e.target.value, 7, 1, 365),
	                  }))
                }
                className="w-20 px-2 py-1 text-sm rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-istara-500"
              />
            </div>

            {/* Save button */}
            <div className="flex justify-end pt-2">
              <button
                onClick={handleSaveConfig}
                disabled={savingConfig}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                  "bg-istara-600 text-white hover:bg-istara-700 disabled:opacity-50"
                )}
              >
                {savingConfig && <RefreshCw size={14} className="animate-spin" />}
                Save Configuration
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
