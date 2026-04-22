"use client";

import { useEffect, useState } from "react";
import { Key, Trash2, RefreshCw, Shield, Fingerprint } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import ConfirmDialog from "@/components/common/ConfirmDialog";

interface Passkey {
  id: string;
  label: string;
  created_at: string;
  last_used_at: string | null;
  authenticator_type: string | null;
}

export default function PasskeyManager() {
  const { registerPasskey, listPasskeys, deletePasskey } = useAuthStore();
  const [passkeys, setPasskeys] = useState<Passkey[]>([]);
  const [loading, setLoading] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const fetchPasskeys = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listPasskeys();
      setPasskeys(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load passkeys");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPasskeys();
  }, []);

  const handleRegister = async () => {
    setRegistering(true);
    setError("");
    try {
      await registerPasskey();
      await fetchPasskeys();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Passkey registration failed");
    } finally {
      setRegistering(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deletePasskey(id);
      await fetchPasskeys();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete passkey");
    } finally {
      setConfirmDelete(null);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
          <Fingerprint size={18} />
          Passkeys
        </h3>
        <button
          onClick={handleRegister}
          disabled={registering}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-istara-600 hover:bg-istara-700 text-white text-sm font-medium transition disabled:opacity-50"
        >
          {registering ? (
            <RefreshCw size={14} className="animate-spin" />
          ) : (
            <Key size={14} />
          )}
          {registering ? "Registering..." : "Register Passkey"}
        </button>
      </div>

      {error && (
        <div className="mb-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {passkeys.length === 0 && !loading ? (
        <div className="text-center py-6 text-slate-400 dark:text-slate-500">
          <Shield size={32} className="mx-auto mb-2 opacity-50" />
          <p className="text-sm">No passkeys registered yet.</p>
          <p className="text-xs mt-1">Register a passkey to sign in without a password.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {passkeys.map((pk) => (
            <div
              key={pk.id}
              className="flex items-center justify-between p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-istara-100 dark:bg-istara-900/30 flex items-center justify-center">
                  <Fingerprint size={14} className="text-istara-600 dark:text-istara-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                    {pk.label || "Passkey"}
                  </p>
                  <p className="text-xs text-slate-400 dark:text-slate-500">
                    Created {new Date(pk.created_at).toLocaleDateString()}
                    {pk.last_used_at && ` · Last used ${new Date(pk.last_used_at).toLocaleDateString()}`}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setConfirmDelete(pk.id)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
                aria-label="Delete passkey"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {loading && passkeys.length === 0 && (
        <div className="flex items-center justify-center py-6 text-slate-400">
          <RefreshCw size={18} className="animate-spin mr-2" />
          Loading passkeys...
        </div>
      )}

      <ConfirmDialog
        open={!!confirmDelete}
        title="Delete Passkey"
        message="Are you sure you want to remove this passkey? You won't be able to sign in with it anymore."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
}
