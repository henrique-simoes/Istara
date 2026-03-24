"use client";

import { useState } from "react";
import { useAuthStore } from "@/stores/authStore";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const { login, register, loading } = useAuthStore();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await register(username, email, password, displayName);
      }
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
      <div className="w-full max-w-md p-8 bg-white dark:bg-slate-900 rounded-xl shadow-lg border border-slate-200 dark:border-slate-800">
        <div className="text-center mb-8">
          <span className="text-4xl">🐾</span>
          <h1 className="text-2xl font-bold mt-2 text-slate-900 dark:text-white">ReClaw</h1>
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
            Register
          </button>
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
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-reclaw-500"
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
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-reclaw-500"
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
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-reclaw-500"
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
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-reclaw-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-reclaw-600 hover:bg-reclaw-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-reclaw-500 focus:ring-offset-2"
          >
            {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}
