"use client";

import { useEffect, useState } from "react";
import { Copy, KeyRound, RefreshCw, Save, ShieldAlert, UserRound } from "lucide-react";

import { useAuthStore } from "@/stores/authStore";

export default function AccountSecurityManager() {
  const { user, updateProfile, changePassword, generateRecoveryCodes } = useAuthStore();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [profilePassword, setProfilePassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [recoveryPassword, setRecoveryPassword] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setUsername(user?.username || "");
    setEmail(user?.email || "");
    setDisplayName(user?.display_name || user?.username || "");
  }, [user]);

  if (!user || user.id === "local") return null;

  const run = async (key: string, action: () => Promise<void>) => {
    setBusy(key);
    setMessage("");
    setError("");
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Security update failed");
    } finally {
      setBusy("");
    }
  };

  const copyRecoveryCodes = async () => {
    if (!recoveryCodes.length) return;
    await navigator.clipboard.writeText(recoveryCodes.join("\n"));
    setMessage("Recovery codes copied. Store them somewhere offline and private.");
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <h3 className="font-medium text-slate-900 dark:text-white mb-2 flex items-center gap-2">
        <UserRound size={18} />
        Account Security
      </h3>
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Update your username, password, and one-time recovery codes. Recovery codes are shown once; if they are lost and no passkey or 2FA access remains, account recovery requires an administrator.
      </p>

      {message && <p className="mt-3 text-sm text-green-700 dark:text-green-400">{message}</p>}
      {error && <p className="mt-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-slate-800 dark:text-slate-200">Profile</h4>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            autoComplete="username"
            className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
          />
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            autoComplete="email"
            className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
          />
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Display name"
            autoComplete="name"
            className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
          />
          <input
            type="password"
            value={profilePassword}
            onChange={(e) => setProfilePassword(e.target.value)}
            placeholder="Current password"
            autoComplete="current-password"
            className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
          />
          <button
            type="button"
            disabled={busy === "profile"}
            onClick={() =>
              run("profile", async () => {
                await updateProfile({
                  current_password: profilePassword,
                  username,
                  email,
                  display_name: displayName,
                });
                setProfilePassword("");
                setMessage("Profile updated.");
              })
            }
            className="inline-flex items-center gap-2 py-2 px-4 rounded-lg bg-istara-600 hover:bg-istara-700 text-white text-sm font-medium disabled:opacity-50"
          >
            {busy === "profile" ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
            Save Profile
          </button>
        </div>

        <div className="space-y-3">
          <h4 className="text-sm font-medium text-slate-800 dark:text-slate-200">Password</h4>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="Current password"
            autoComplete="current-password"
            className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
          />
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="New password"
            autoComplete="new-password"
            className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
          />
          <button
            type="button"
            disabled={busy === "password"}
            onClick={() =>
              run("password", async () => {
                await changePassword(currentPassword, newPassword);
                setCurrentPassword("");
                setNewPassword("");
                setMessage("Password changed. Other sessions were revoked where possible.");
              })
            }
            className="inline-flex items-center gap-2 py-2 px-4 rounded-lg bg-istara-600 hover:bg-istara-700 text-white text-sm font-medium disabled:opacity-50"
          >
            {busy === "password" ? <RefreshCw size={14} className="animate-spin" /> : <KeyRound size={14} />}
            Change Password
          </button>
        </div>
      </div>

      <div className="mt-5 rounded-lg border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/30 p-4">
        <h4 className="text-sm font-medium text-amber-900 dark:text-amber-200 flex items-center gap-2">
          <ShieldAlert size={16} />
          Recovery Codes
        </h4>
        <p className="mt-1 text-xs text-amber-800 dark:text-amber-300">
          Regenerating recovery codes invalidates previous codes. Save the new set before leaving this screen.
        </p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <input
            type="password"
            value={recoveryPassword}
            onChange={(e) => setRecoveryPassword(e.target.value)}
            placeholder="Current password"
            autoComplete="current-password"
            className="flex-1 px-3 py-2.5 rounded-lg border border-amber-300 dark:border-amber-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
          />
          <button
            type="button"
            disabled={busy === "recovery"}
            onClick={() =>
              run("recovery", async () => {
                const codes = await generateRecoveryCodes(recoveryPassword);
                setRecoveryCodes(codes);
                setRecoveryPassword("");
                setMessage("New recovery codes generated. Save them now.");
              })
            }
            className="inline-flex items-center justify-center gap-2 py-2 px-4 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium disabled:opacity-50"
          >
            {busy === "recovery" ? <RefreshCw size={14} className="animate-spin" /> : <KeyRound size={14} />}
            Generate Codes
          </button>
        </div>
        {recoveryCodes.length > 0 && (
          <div className="mt-3">
            <div className="grid grid-cols-2 gap-2 rounded-lg bg-white dark:bg-slate-900 border border-amber-200 dark:border-amber-900 p-3 font-mono text-sm text-slate-900 dark:text-slate-100">
              {recoveryCodes.map((code) => (
                <span key={code}>{code}</span>
              ))}
            </div>
            <button
              type="button"
              onClick={copyRecoveryCodes}
              className="mt-2 inline-flex items-center gap-2 py-1.5 px-3 rounded-lg border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-sm"
            >
              <Copy size={14} />
              Copy Codes
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
