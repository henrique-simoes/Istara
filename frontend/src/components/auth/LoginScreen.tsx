"use client";

import { useState, useRef, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface LoginScreenProps {
  onLogin: () => void;
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [teamMode, setTeamMode] = useState(false);
  const [hasUsers, setHasUsers] = useState(true);
  const usernameRef = useRef<HTMLInputElement>(null);

  // Check team status on mount — determines if registration is available
  useEffect(() => {
    fetch(`${API_BASE}/api/auth/team-status`)
      .then((r) => r.json())
      .then((d) => {
        setTeamMode(d.team_mode || false);
        setHasUsers(d.has_users !== false);
        // Fresh server with team mode + no users → show register directly
        if (d.team_mode && d.has_users === false) {
          setMode("register");
        }
      })
      .catch(() => {});
  }, []);

  // Auto-focus username input on mount
  useEffect(() => {
    usernameRef.current?.focus();
  }, [mode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!username.trim() || !password.trim()) {
      setError("Username and password are required.");
      return;
    }
    if (mode === "register" && !email.trim()) {
      setError("Email is required for registration.");
      return;
    }

    setLoading(true);
    try {
      const endpoint = mode === "register" ? "/api/auth/register" : "/api/auth/login";
      const body = mode === "register"
        ? { username: username.trim(), password, email: email.trim(), display_name: username.trim() }
        : { username: username.trim(), password };

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: `${mode === "register" ? "Registration" : "Login"} failed` }));
        throw new Error(data.detail || `Failed (${res.status})`);
      }

      const data = await res.json();
      localStorage.setItem("reclaw_token", data.token);
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4">
      <div className="w-full max-w-md">
        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 p-8">
          {/* Logo and title */}
          <div className="text-center mb-8">
            <div className="text-5xl mb-3" role="img" aria-label="ReClaw logo">
              🐾
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
              ReClaw
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Local-first AI for UX Research
            </p>
            {mode === "register" && !hasUsers && (
              <p className="text-xs text-reclaw-600 dark:text-reclaw-400 mt-2 font-medium">
                First user — you will be the admin.
              </p>
            )}
          </div>

          {/* Login form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="login-username"
                className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >
                Username
              </label>
              <input
                ref={usernameRef}
                id="login-username"
                type="text"
                aria-label="Username"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={loading}
                className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-reclaw-500 focus:border-transparent transition disabled:opacity-50"
                placeholder="Enter your username"
              />
            </div>

            {mode === "register" && (
              <div>
                <label
                  htmlFor="login-email"
                  className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >
                  Email
                </label>
                <input
                  id="login-email"
                  type="email"
                  aria-label="Email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-reclaw-500 focus:border-transparent transition disabled:opacity-50"
                  placeholder="you@company.com"
                />
              </div>
            )}

            <div>
              <label
                htmlFor="login-password"
                className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >
                Password
              </label>
              <input
                id="login-password"
                type="password"
                aria-label="Password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-reclaw-500 focus:border-transparent transition disabled:opacity-50"
                placeholder="Enter your password"
              />
            </div>

            {/* Error message */}
            {error && (
              <div
                role="alert"
                className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-lg bg-reclaw-600 hover:bg-reclaw-700 active:bg-reclaw-800 text-white font-medium transition focus:outline-none focus:ring-2 focus:ring-reclaw-500 focus:ring-offset-2 dark:focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="inline-flex items-center gap-2">
                  <svg
                    className="animate-spin h-4 w-4"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Signing in...
                </span>
              ) : (
                mode === "register" ? "Create Account" : "Sign In"
              )}
            </button>
          </form>

          {/* Footer — toggle between login/register */}
          {teamMode && (
            <div className="mt-6 text-center">
              {mode === "login" ? (
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  New to this server?{" "}
                  <button
                    type="button"
                    onClick={() => { setMode("register"); setError(""); }}
                    className="text-reclaw-600 dark:text-reclaw-400 font-medium hover:underline"
                  >
                    Create an account
                  </button>
                </p>
              ) : (
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => { setMode("login"); setError(""); }}
                    className="text-reclaw-600 dark:text-reclaw-400 font-medium hover:underline"
                  >
                    Sign in
                  </button>
                </p>
              )}
            </div>
          )}
          {!teamMode && (
            <p className="mt-6 text-center text-xs text-slate-400 dark:text-slate-500">
              Local mode — enter any username and password to continue.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
