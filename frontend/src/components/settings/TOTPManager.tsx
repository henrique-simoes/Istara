"use client";

import { useState } from "react";
import { ShieldCheck, ShieldOff } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function TOTPManager() {
  const { user, token, fetchMe } = useAuthStore();
  const [secret, setSecret] = useState("");
  const [provisioningUri, setProvisioningUri] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const startSetup = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await fetch(`${API_BASE}/api/auth/totp/setup`, {
        method: "POST",
        headers,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to start 2FA setup" }));
        throw new Error(data.detail || "Failed to start 2FA setup");
      }
      const data = await res.json();
      setSecret(data.secret || "");
      setProvisioningUri(data.provisioning_uri || "");
      setMessage("Add this secret to your authenticator app, then enter the 6-digit code.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start 2FA setup");
    } finally {
      setLoading(false);
    }
  };

  const verifySetup = async () => {
    if (!code.trim()) {
      setError("Enter the 6-digit code from your authenticator app.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/auth/totp/verify`, {
        method: "POST",
        headers,
        body: JSON.stringify({ totp_code: code.trim() }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to verify 2FA code" }));
        throw new Error(data.detail || "Failed to verify 2FA code");
      }
      setSecret("");
      setProvisioningUri("");
      setCode("");
      setMessage("Two-factor authentication is enabled.");
      await fetchMe();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to verify 2FA code");
    } finally {
      setLoading(false);
    }
  };

  const disable = async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await fetch(`${API_BASE}/api/auth/totp/disable`, {
        method: "POST",
        headers,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to disable 2FA" }));
        throw new Error(data.detail || "Failed to disable 2FA");
      }
      setMessage("Two-factor authentication is disabled.");
      await fetchMe();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to disable 2FA");
    } finally {
      setLoading(false);
    }
  };

  if (!user || user.id === "local") return null;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <h3 className="font-medium text-slate-900 dark:text-white mb-2 flex items-center gap-2">
        {user.totp_enabled ? <ShieldCheck size={18} /> : <ShieldOff size={18} />}
        Two-Factor Authentication
      </h3>
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Protect team accounts with a 6-digit authenticator code. Recovery codes generated at account creation remain the backup path.
      </p>

      {message && <p className="mt-3 text-sm text-green-700 dark:text-green-400">{message}</p>}
      {error && <p className="mt-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      {secret ? (
        <div className="mt-4 space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
              Authenticator secret
            </label>
            <code className="block rounded-lg bg-slate-100 dark:bg-slate-900 px-3 py-2 text-sm break-all text-slate-800 dark:text-slate-100">
              {secret}
            </code>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
              Provisioning URI
            </label>
            <code className="block rounded-lg bg-slate-100 dark:bg-slate-900 px-3 py-2 text-xs break-all text-slate-800 dark:text-slate-100">
              {provisioningUri}
            </code>
          </div>
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            placeholder="000000"
            className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white text-center tracking-widest"
          />
          <button
            type="button"
            onClick={verifySetup}
            disabled={loading}
            className="w-full py-2 px-4 rounded-lg bg-istara-600 hover:bg-istara-700 text-white text-sm font-medium disabled:opacity-50"
          >
            Verify and Enable
          </button>
        </div>
      ) : (
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={startSetup}
            disabled={loading}
            className="py-2 px-4 rounded-lg bg-istara-600 hover:bg-istara-700 text-white text-sm font-medium disabled:opacity-50"
          >
            Set Up 2FA
          </button>
          <button
            type="button"
            onClick={disable}
            disabled={loading}
            className="py-2 px-4 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-sm font-medium disabled:opacity-50"
          >
            Disable
          </button>
        </div>
      )}
    </div>
  );
}
