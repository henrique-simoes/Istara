"use client";

import { useState, useRef, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface LoginScreenProps {
  onLogin: () => Promise<boolean | void>;
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "register" | "join">("login");
  const [teamMode, setTeamMode] = useState(false);
  const [hasUsers, setHasUsers] = useState(true);
  const [insecure, setInsecure] = useState(false);
  const [connectionString, setConnectionString] = useState("");
  const [joinValidated, setJoinValidated] = useState<any>(null);
  const [serverReachable, setServerReachable] = useState<boolean | null>(null);
  const usernameRef = useRef<HTMLInputElement>(null);

  // Check team status on mount — determines UI mode.
  // Retries up to 5 times with 2s backoff to handle backend startup races.
  useEffect(() => {
    let cancelled = false;

    const checkServer = async (attempt = 0): Promise<void> => {
      try {
        const res = await fetch(`${API_BASE}/api/auth/team-status`, {
          signal: AbortSignal.timeout(5000),
        });
        const d = await res.json();
        if (!cancelled) {
          setTeamMode(d.team_mode || false);
          setHasUsers(d.has_users !== false);
          setInsecure(d.insecure || false);
          setServerReachable(true);
          if (d.team_mode && d.has_users === false) {
            setMode("register");
          } else if (!d.team_mode && d.insecure) {
            setMode("join");
          }
        }
      } catch {
        if (!cancelled && attempt < 5) {
          await new Promise((r) => setTimeout(r, 2000));
          await checkServer(attempt + 1);
        } else if (!cancelled) {
          setServerReachable(false);
        }
      }
    };

    checkServer();
    return () => { cancelled = true; };
  }, []);

  // Auto-focus username input
  useEffect(() => {
    usernameRef.current?.focus();
  }, [mode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Join mode: first validate, then redeem
    if (mode === "join") {
      if (!joinValidated) {
        if (!connectionString.trim()) { setError("Paste a connection string."); return; }
        setLoading(true);
        try {
          const res = await fetch(`${API_BASE}/api/connections/validate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ connection_string: connectionString.trim() }),
          });
          const data = await res.json();
          if (!data.valid) { throw new Error(data.error || "Invalid connection string"); }
          setJoinValidated(data);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Invalid connection string");
        } finally { setLoading(false); }
        return;
      }
      if (!username.trim() || !password.trim()) { setError("Choose a username and password."); return; }
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/connections/redeem`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            connection_string: connectionString.trim(),
            username: username.trim(),
            password,
            email: email.trim(),
          }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({ detail: "Failed" }));
          throw new Error(data.detail || "Redemption failed");
        }
        const data = await res.json();
        localStorage.setItem("istara_token", data.token);
        await onLogin();
      } catch (err) {
        if (err instanceof TypeError && err.message === "Failed to fetch") {
          setError("Cannot connect to the server. Make sure the backend is running.");
        } else {
          setError(err instanceof Error ? err.message : "Something went wrong.");
        }
      } finally { setLoading(false); }
      return;
    }

    // Local mode — only name is required
    if (!teamMode) {
      if (!username.trim()) {
        setError("Enter your name to continue.");
        return;
      }
    } else {
      // Team mode — username and password required
      if (!username.trim() || !password.trim()) {
        setError("Username and password are required.");
        return;
      }
      if (mode === "register" && !email.trim()) {
        setError("Email is required for registration.");
        return;
      }
    }

    setLoading(true);
    try {
      const endpoint = mode === "register" ? "/api/auth/register" : "/api/auth/login";
      const body = mode === "register"
        ? { username: username.trim(), password, email: email.trim(), display_name: username.trim() }
        : { username: username.trim(), password: password || "local" };

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
      localStorage.setItem("istara_token", data.token);
      await onLogin();
    } catch (err) {
      if (err instanceof TypeError && err.message === "Failed to fetch") {
        setError("Cannot connect to the Istara server. Make sure the backend is running on port 8000.");
      } else {
        setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  // ── Server not reachable ──────────────────────────────────
  if (serverReachable === false) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4">
        <div className="w-full max-w-md">
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 p-8">
            <div className="text-center mb-6">
              <div className="text-5xl mb-3" role="img" aria-label="Istara logo">🐾</div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Istara</h1>
            </div>
            <div className="rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 p-4 text-center">
              <p className="text-amber-800 dark:text-amber-300 font-medium text-sm">
                Cannot connect to the Istara server
              </p>
              <p className="text-amber-600 dark:text-amber-400 text-xs mt-2">
                The backend API at <code className="bg-amber-100 dark:bg-amber-900/50 px-1 rounded">{API_BASE}</code> is not responding.
              </p>
              <div className="mt-4 text-xs text-slate-500 dark:text-slate-400 space-y-1">
                <p>Start the server with:</p>
                <code className="block bg-slate-100 dark:bg-slate-800 px-3 py-2 rounded font-mono text-slate-700 dark:text-slate-300">
                  istara start
                </code>
              </div>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 w-full py-2 px-4 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-sm hover:bg-slate-50 dark:hover:bg-slate-800 transition"
            >
              Retry Connection
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Local mode — welcoming first-run experience ───────────
  if (!teamMode && !insecure && mode === "login") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4">
        <div className="w-full max-w-md">
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 p-8">
            <div className="text-center mb-6">
              <div className="text-5xl mb-3" role="img" aria-label="Istara logo">🐾</div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                Welcome to Istara
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                Local-first AI agents for UX Research
              </p>
            </div>

            {insecure && (
              <div className="mb-6 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 p-4">
                <div className="flex items-start gap-3">
                  <div className="text-red-600 dark:text-red-400 mt-0.5">⚠️</div>
                  <div>
                    <p className="text-sm font-bold text-red-800 dark:text-red-300">
                      Insecure Mode Detected
                    </p>
                    <p className="text-xs text-red-700 dark:text-red-400 mt-1 leading-relaxed">
                      This server is accessible over the network but has authentication disabled. 
                      Anyone with the URL can access all research data.
                    </p>
                    <div className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                      <p>To secure your server:</p>
                      <code className="block bg-white/50 dark:bg-black/20 p-2 rounded mt-1 font-mono">
                        TEAM_MODE=true
                      </code>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label
                  htmlFor="login-username"
                  className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >
                  Your Name
                </label>
                <input
                  ref={usernameRef}
                  id="login-username"
                  type="text"
                  aria-label="Your name"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-istara-500 focus:border-transparent transition disabled:opacity-50"
                  placeholder="e.g. Sarah, John, Research Team"
                />
              </div>

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
                disabled={loading || !username.trim()}
                className="w-full py-2.5 px-4 rounded-lg bg-istara-600 hover:bg-istara-700 active:bg-istara-800 text-white font-medium transition focus:outline-none focus:ring-2 focus:ring-istara-500 focus:ring-offset-2 dark:focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Getting started...
                  </span>
                ) : (
                  "Get Started"
                )}
              </button>
            </form>

            <p className="mt-6 text-center text-xs text-slate-400 dark:text-slate-500">
              Single-user mode. Your data stays on this machine.
              <br />
              <span className="text-slate-400 dark:text-slate-600">
                Enable Team Mode in Settings for multi-user collaboration.
              </span>
              <br />
              <span className="text-amber-500 dark:text-amber-400">
                Local mode — no HTTPS. Use production profile for secure connections.
              </span>
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ── Team mode: login / register / join ────────────────────
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4">
      <div className="w-full max-w-md">
        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 p-8">
          {/* Logo and title */}
          <div className="text-center mb-8">
            <div className="text-5xl mb-3" role="img" aria-label="Istara logo">
              🐾
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
              {mode === "register" && !hasUsers
                ? "Create Admin Account"
                : mode === "register"
                ? "Create Account"
                : mode === "join"
                ? "Join Server"
                : "Sign In"
              }
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              {!teamMode && insecure
                ? "This server is in Individual Mode. Enter a connection string to access."
                : mode === "register" && !hasUsers
                ? "You'll be the admin for this Istara server."
                : "Local-first AI agents for UX Research"
              }
            </p>
          </div>

          {/* Banner for members who have a connection string */}
          {mode === "login" && (
            <div className="mb-4 rounded-lg bg-istara-50 dark:bg-istara-900/20 border border-istara-200 dark:border-istara-800 px-4 py-3 text-center">
              <p className="text-xs text-istara-700 dark:text-istara-400">
                Got a connection string from your admin?{" "}
                <button type="button" onClick={() => { setMode("join"); setError(""); }} className="font-semibold underline hover:text-istara-800 dark:hover:text-istara-300">
                  Join Server →
                </button>
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Join Server: connection string input */}
            {mode === "join" && !joinValidated && (
              <div>
                <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-3 mb-4">
                  <p className="text-blue-700 dark:text-blue-400 text-xs leading-relaxed">
                    Your admin should have given you a connection string that starts with <code className="bg-blue-100 dark:bg-blue-900/50 px-1 rounded">rcl_</code>.
                    Paste it below to connect to the team server.
                  </p>
                </div>
                <label
                  htmlFor="join-connection-string"
                  className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
                >
                  Connection String
                </label>
                <textarea
                  id="join-connection-string"
                  aria-label="Connection string"
                  value={connectionString}
                  onChange={(e) => setConnectionString(e.target.value)}
                  disabled={loading}
                  rows={3}
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-istara-500 transition disabled:opacity-50 text-xs font-mono"
                  placeholder="rcl_eyJ2Ijo..."
                />
              </div>
            )}
            {mode === "join" && joinValidated && (
              <div className="rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-3 text-sm">
                <p className="text-green-700 dark:text-green-400 font-medium">Server verified ✓</p>
                <p className="text-green-600 dark:text-green-500 text-xs mt-1">
                  {joinValidated.server_url} {joinValidated.label && `(${joinValidated.label})`}
                </p>
                <p className="text-slate-500 text-xs mt-2">
                  Choose a username and password for your new account.
                  {teamMode && (
                    <span>
                      {" "}If your admin already created one for you, <button type="button" onClick={() => { setMode("login"); setError(""); setJoinValidated(null); }} className="text-istara-600 dark:text-istara-400 font-medium hover:underline">go to Sign In</button> instead.
                    </span>
                  )}
                </p>
              </div>
            )}

            {/* Username — shown for login, register, and join (after validation) */}
            {(mode !== "join" || joinValidated) && (
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
                className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-istara-500 focus:border-transparent transition disabled:opacity-50"
                placeholder="Choose a username"
              />
            </div>
            )}

            {(mode === "register" || (mode === "join" && joinValidated)) && (
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
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-istara-500 focus:border-transparent transition disabled:opacity-50"
                  placeholder="you@company.com"
                />
              </div>
            )}

            {/* Password — only in team mode */}
            {(mode !== "join" || joinValidated) && (
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
                autoComplete={mode === "register" ? "new-password" : "current-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-istara-500 focus:border-transparent transition disabled:opacity-50"
                placeholder={mode === "register" ? "At least 8 characters" : "Enter your password"}
              />
            </div>
            )}

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
              className="w-full py-2.5 px-4 rounded-lg bg-istara-600 hover:bg-istara-700 active:bg-istara-800 text-white font-medium transition focus:outline-none focus:ring-2 focus:ring-istara-500 focus:ring-offset-2 dark:focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="inline-flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {mode === "register" ? "Creating account..." : mode === "join" ? "Connecting..." : "Signing in..."}
                </span>
              ) : (
                mode === "join"
                  ? (joinValidated ? "Create Account & Connect" : "Verify Connection")
                  : mode === "register" ? "Create Account" : "Sign In"
              )}
            </button>
          </form>

          {/* Footer — toggle between login/register/join */}
          {teamMode && (
            <div className="mt-6 text-center space-y-1">
              {mode !== "login" && (
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  Already have an account?{" "}
                  <button type="button" onClick={() => { setMode("login"); setError(""); setJoinValidated(null); }}
                    className="text-istara-600 dark:text-istara-400 font-medium hover:underline">Sign in</button>
                </p>
              )}
              {mode !== "register" && (
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  New to this server?{" "}
                  <button type="button" onClick={() => { setMode("register"); setError(""); setJoinValidated(null); }}
                    className="text-istara-600 dark:text-istara-400 font-medium hover:underline">Create an account</button>
                </p>
              )}
              {mode !== "join" && (
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  Have a connection string?{" "}
                  <button type="button" onClick={() => { setMode("join"); setError(""); setJoinValidated(null); }}
                    className="text-istara-600 dark:text-istara-400 font-medium hover:underline">Join Server</button>
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
