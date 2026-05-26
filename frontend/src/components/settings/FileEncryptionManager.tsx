"use client";

import { useCallback, useEffect, useState } from "react";
import { KeyRound, LockKeyhole, RefreshCw, RotateCw, ShieldAlert } from "lucide-react";

import { settings as settingsApi } from "@/lib/api";
import { useRoleCapabilities } from "@/hooks/useRoleCapabilities";

interface FileEncryptionStatus {
  enabled: boolean;
  crypto_available: boolean;
  key_available: boolean;
  key_storage: string;
  key_fingerprint: string;
  managed_file_count: number;
  encrypted_file_count: number;
  backups_encrypted_when_enabled: boolean;
  warning: string;
}

export default function FileEncryptionManager() {
  const capabilities = useRoleCapabilities();
  const [status, setStatus] = useState<FileEncryptionStatus | null>(null);
  const [confirmEnable, setConfirmEnable] = useState(false);
  const [confirmRotate, setConfirmRotate] = useState(false);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!capabilities.canManageSystemSettings) return;
    setError("");
    try {
      setStatus(await settingsApi.fileEncryptionStatus());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load file encryption status");
    }
  }, [capabilities.canManageSystemSettings]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (!capabilities.canManageSystemSettings) return null;

  const run = async (key: string, action: () => Promise<void>) => {
    setBusy(key);
    setMessage("");
    setError("");
    try {
      await action();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "File encryption update failed");
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <h3 className="font-medium text-slate-900 dark:text-white mb-2 flex items-center gap-2">
        <LockKeyhole size={18} />
        File and Backup Encryption
      </h3>
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Encrypt managed uploads, stored document text, and future backup archives at rest. Keep the key in a secrets manager, macOS Keychain, or the owner-only fallback key file; losing it makes encrypted files and backups unrecoverable.
      </p>

      {message && <p className="mt-3 text-sm text-green-700 dark:text-green-400">{message}</p>}
      {error && <p className="mt-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
        <div className="rounded-lg bg-slate-50 dark:bg-slate-900 p-3">
          <p className="text-slate-500">Status</p>
          <p className="font-medium text-slate-900 dark:text-white">
            {status?.enabled ? "Enabled" : "Disabled"}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 dark:bg-slate-900 p-3">
          <p className="text-slate-500">Key</p>
          <p className="font-medium text-slate-900 dark:text-white">
            {status?.key_available ? status.key_fingerprint || "available" : "missing"}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 dark:bg-slate-900 p-3">
          <p className="text-slate-500">Managed Files</p>
          <p className="font-medium text-slate-900 dark:text-white">
            {status ? `${status.encrypted_file_count}/${status.managed_file_count}` : "-"}
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 dark:bg-slate-900 p-3">
          <p className="text-slate-500">Storage</p>
          <p className="font-medium text-slate-900 dark:text-white break-words">
            {status?.key_storage || "-"}
          </p>
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/30 p-3 text-xs text-amber-800 dark:text-amber-300">
        <div className="flex gap-2">
          <ShieldAlert size={16} className="mt-0.5 shrink-0" />
          <p>{status?.warning || "The encryption key is required to restore encrypted backups and read encrypted project content."}</p>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-3">
        {!status?.enabled && (
          <label className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              checked={confirmEnable}
              onChange={(e) => setConfirmEnable(e.target.checked)}
              className="mt-1"
            />
            I understand Istara will encrypt existing managed project uploads, stored document text, and future backups, and that losing the key is destructive.
          </label>
        )}
        {status?.enabled && (
          <label className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              checked={confirmRotate}
              onChange={(e) => setConfirmRotate(e.target.checked)}
              className="mt-1"
            />
            I have a current backup and understand key rotation rewrites encrypted managed files, document text, and future backup key material.
          </label>
        )}

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={refresh}
            className="inline-flex items-center gap-2 py-2 px-4 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-sm"
          >
            <RefreshCw size={14} />
            Refresh
          </button>
          {!status?.enabled ? (
            <button
              type="button"
              disabled={!confirmEnable || busy === "enable" || status?.crypto_available === false}
              onClick={() =>
                run("enable", async () => {
                  await settingsApi.enableFileEncryption();
                  setConfirmEnable(false);
                  setMessage("File encryption enabled and existing managed content migrated.");
                })
              }
              className="inline-flex items-center gap-2 py-2 px-4 rounded-lg bg-istara-600 hover:bg-istara-700 text-white text-sm font-medium disabled:opacity-50"
            >
              {busy === "enable" ? <RefreshCw size={14} className="animate-spin" /> : <KeyRound size={14} />}
              Enable Encryption
            </button>
          ) : (
            <button
              type="button"
              disabled={!confirmRotate || busy === "rotate"}
              onClick={() =>
                run("rotate", async () => {
                  await settingsApi.rotateFileEncryptionKey();
                  setConfirmRotate(false);
                  setMessage("File encryption key rotated.");
                })
              }
              className="inline-flex items-center gap-2 py-2 px-4 rounded-lg bg-istara-600 hover:bg-istara-700 text-white text-sm font-medium disabled:opacity-50"
            >
              {busy === "rotate" ? <RefreshCw size={14} className="animate-spin" /> : <RotateCw size={14} />}
              Rotate Key
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
