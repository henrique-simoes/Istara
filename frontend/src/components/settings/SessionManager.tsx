"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Clock, LogOut, MonitorSmartphone, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";

import ConfirmDialog from "@/components/common/ConfirmDialog";
import { useAuthStore, type AuthSession } from "@/stores/authStore";

type PendingAction =
  | { kind: "one"; session: AuthSession }
  | { kind: "others" }
  | null;

function formatDate(value: string | null): string {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function summarizeDevice(userAgent: string): string {
  if (!userAgent) return "Unknown device";
  const browser =
    userAgent.includes("Firefox") ? "Firefox" :
    userAgent.includes("Edg/") ? "Edge" :
    userAgent.includes("Chrome") ? "Chrome" :
    userAgent.includes("Safari") ? "Safari" :
    "Browser";
  const os =
    userAgent.includes("Windows") ? "Windows" :
    userAgent.includes("Mac OS X") ? "macOS" :
    userAgent.includes("Linux") ? "Linux" :
    userAgent.includes("Android") ? "Android" :
    userAgent.includes("iPhone") || userAgent.includes("iPad") ? "iOS" :
    "";
  return os ? `${browser} on ${os}` : browser;
}

export default function SessionManager() {
  const {
    user,
    listAuthSessions,
    revokeAuthSession,
    revokeOtherAuthSessions,
    logout,
  } = useAuthStore();
  const [sessions, setSessions] = useState<AuthSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState<PendingAction>(null);

  const fetchSessions = useCallback(async () => {
    if (!user || user.id === "local") return;
    setLoading(true);
    setError("");
    try {
      setSessions(await listAuthSessions());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  }, [listAuthSessions, user]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const otherSessionCount = useMemo(
    () => sessions.filter((session) => !session.current).length,
    [sessions]
  );

  const confirmTitle = pending?.kind === "others"
    ? "Revoke Other Sessions"
    : pending?.session.current
    ? "Sign Out This Device"
    : "Revoke Session";
  const confirmMessage = pending?.kind === "others"
    ? "Other devices will need to sign in again."
    : pending?.session.current
    ? "This device will be signed out immediately."
    : "That device will need to sign in again.";
  const confirmLabel = pending?.kind === "others"
    ? "Revoke Others"
    : pending?.session.current
    ? "Sign Out"
    : "Revoke";

  const handleConfirm = async () => {
    if (!pending) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (pending.kind === "others") {
        const result = await revokeOtherAuthSessions();
        setMessage(`${result.revoked_count} session${result.revoked_count === 1 ? "" : "s"} revoked.`);
        await fetchSessions();
      } else {
        const result = await revokeAuthSession(pending.session.id);
        if (result.revoked_current) {
          await logout();
          return;
        }
        setMessage(result.revoked ? "Session revoked." : "Session was already inactive.");
        await fetchSessions();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to revoke session");
    } finally {
      setBusy(false);
      setPending(null);
    }
  };

  if (!user || user.id === "local") return null;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
          <ShieldCheck size={18} />
          Active Sessions
        </h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchSessions}
            disabled={loading || busy}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-300 disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => setPending({ kind: "others" })}
            disabled={busy || otherSessionCount === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-medium disabled:opacity-50"
          >
            <LogOut size={14} />
            Revoke Others
          </button>
        </div>
      </div>

      {message && <p className="mb-3 text-sm text-green-700 dark:text-green-400">{message}</p>}
      {error && <p className="mb-3 text-sm text-red-700 dark:text-red-400">{error}</p>}

      {sessions.length === 0 && !loading ? (
        <div className="py-6 text-center text-sm text-slate-500 dark:text-slate-400">
          No active sessions.
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 p-3"
            >
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-istara-100 dark:bg-istara-900/30">
                  <MonitorSmartphone size={16} className="text-istara-600 dark:text-istara-400" />
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">
                      {session.current ? "This device" : summarizeDevice(session.user_agent)}
                    </p>
                    {session.current && (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300">
                        Current
                      </span>
                    )}
                    {session.mfa_verified && (
                      <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                        MFA
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                    <span className="font-mono">{session.ip_address || "unknown IP"}</span>
                    <span>{session.auth_method}</span>
                    <span className="inline-flex items-center gap-1">
                      <Clock size={12} />
                      Last used {formatDate(session.last_seen_at)}
                    </span>
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setPending({ kind: "one", session })}
                disabled={busy}
                aria-label={session.current ? "Sign out this device" : "Revoke session"}
                className="inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 dark:hover:bg-red-900/20"
              >
                {session.current ? <LogOut size={14} /> : <Trash2 size={14} />}
                {session.current ? "Sign Out" : "Revoke"}
              </button>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={!!pending}
        title={confirmTitle}
        message={confirmMessage}
        confirmLabel={confirmLabel}
        variant="danger"
        onConfirm={handleConfirm}
        onCancel={() => setPending(null)}
      />
    </div>
  );
}
