"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/authStore";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [codesSaved, setCodesSaved] = useState(false);
  const [passkeyBusy, setPasskeyBusy] = useState(false);
  const [error, setError] = useState("");
  const [hasUsers, setHasUsers] = useState(true);
  const { login, register, registerPasskey, loading, checkTeamStatus } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    checkTeamStatus().then((status) => {
      if (cancelled) return;
      setHasUsers(status.has_users);
      if (status.has_users) setMode("login");
      if (!status.has_users) setMode("register");
    });
    return () => { cancelled = true; };
  }, [checkTeamStatus]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        if (hasUsers) {
          throw new Error("Public registration is only available for the first admin. Ask an admin for a connection string.");
        }
        const result = await register(username, email, password, displayName);
        setRecoveryCodes(result.recovery_codes || []);
        setCodesSaved(false);
        return;
      }
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    }
  };

  const handlePasskeySetup = async () => {
    setPasskeyBusy(true);
    setError("");
    try {
      await registerPasskey();
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Passkey setup failed. You can set it up later in Settings.");
    } finally {
      setPasskeyBusy(false);
    }
  };

  if (recoveryCodes.length > 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="w-full max-w-lg p-8 bg-white dark:bg-slate-900 rounded-xl shadow-lg border border-slate-200 dark:border-slate-800">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Save your recovery codes</h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            These codes are shown once. Save them somewhere private and offline before continuing.
          </p>
          <div className="mt-5 grid grid-cols-2 gap-2 font-mono text-sm">
            {recoveryCodes.map((code) => (
              <code key={code} className="rounded-lg bg-slate-100 dark:bg-slate-800 px-3 py-2 text-center text-slate-800 dark:text-slate-100">
                {code}
              </code>
            ))}
          </div>
          <label className="mt-5 flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              checked={codesSaved}
              onChange={(e) => setCodesSaved(e.target.checked)}
              className="mt-1"
            />
            I saved these recovery codes somewhere private and offline.
          </label>
          {error && <p className="mt-3 text-sm text-amber-700 dark:text-amber-300">{error}</p>}
          <button
            type="button"
            disabled={!codesSaved || passkeyBusy}
            onClick={handlePasskeySetup}
            className="mt-5 w-full py-2.5 bg-istara-600 hover:bg-istara-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {passkeyBusy ? "Setting up passkey..." : "Set up passkey now"}
          </button>
          <button
            type="button"
            disabled={!codesSaved || passkeyBusy}
            onClick={() => router.push("/")}
            className="mt-3 w-full py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-medium disabled:opacity-50"
          >
            Do this later
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
      <div className="w-full max-w-md p-8 bg-white dark:bg-slate-900 rounded-xl shadow-lg border border-slate-200 dark:border-slate-800">
        <div className="text-center mb-8">
          <span className="text-4xl">🐾</span>
          <h1 className="text-2xl font-bold mt-2 text-slate-900 dark:text-white">Istara</h1>
          <p className="text-sm text-slate-500 mt-1">AI-Powered UX Research Platform</p>
        </div>

        <div className="flex mb-6 bg-slate-100 dark:bg-slate-800 rounded-lg p-1" role="tablist">
          <button
            role="tab"
            aria-selected={mode === "login"}
            onClick={() => setMode("login")}
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
              mode === "login"
                ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm"
                : "text-slate-500"
            }`}
          >
            Sign In
          </button>
          {!hasUsers && (
            <button
              role="tab"
              aria-selected={mode === "register"}
              onClick={() => setMode("register")}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                mode === "register"
                  ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm"
                  : "text-slate-500"
              }`}
            >
              Create Admin
            </button>
          )}
        </div>

        {error && (
          <div role="alert" className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-istara-500"
            />
          </div>

          {mode === "register" && (
            <>
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-istara-500"
                />
              </div>
              <div>
                <label htmlFor="displayName" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Display Name
                </label>
                <input
                  id="displayName"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  autoComplete="name"
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-istara-500"
                />
              </div>
            </>
          )}

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-istara-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-istara-600 hover:bg-istara-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-istara-500 focus:ring-offset-2"
          >
            {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Admin Account"}
          </button>
        </form>
      </div>
    </div>
  );
}
