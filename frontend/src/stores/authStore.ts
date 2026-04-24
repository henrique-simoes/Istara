/** Auth store — manages user authentication state for team mode. */

import { create } from "zustand";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  display_name: string;
  preferences: Record<string, unknown>;
}

interface LoginResult {
  requires_2fa?: boolean;
  methods?: string[];
  token?: string;
  user?: User;
}

interface AuthState {
  user: User | null;
  token: string | null;
  teamMode: boolean;
  hasUsers: boolean;
  insecure: boolean;
  loading: boolean;

  login: (username: string, password: string) => Promise<LoginResult>;
  verify2FA: (username: string, password: string, code: string, method: "totp" | "recovery_code") => Promise<void>;
  register: (username: string, email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
  checkTeamStatus: () => Promise<{ team_mode: boolean; has_users: boolean; insecure: boolean }>;
  fetchMe: () => Promise<boolean>;
  updatePreferences: (prefs: Record<string, unknown>) => Promise<void>;
  getAuthHeaders: () => Record<string, string>;

  // Passkey / WebAuthn
  loginWithPasskey: (username: string) => Promise<void>;
  registerPasskey: () => Promise<void>;
  listPasskeys: () => Promise<Array<{ id: string; label: string; created_at: string; last_used_at: string | null; authenticator_type: string | null }>>;
  deletePasskey: (credentialId: string) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: typeof window !== "undefined" ? localStorage.getItem("istara_token") : null,
  teamMode: false,
  hasUsers: true,
  insecure: false,
  loading: false,

  login: async (username, password) => {
    set({ loading: true });
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Login failed" }));
        throw new Error(err.detail || "Login failed");
      }
      const data = await res.json();
      if (data.requires_2fa) {
        set({ loading: false });
        return { requires_2fa: true, methods: data.methods || ["totp", "recovery_code"] };
      }
      localStorage.setItem("istara_token", data.token);
      if (data.user?.id) localStorage.setItem("istara_auth_user_id", data.user.id);
      set({ user: data.user, token: data.token, loading: false });
      get().checkTeamStatus();
      return { token: data.token, user: data.user };
    } catch (e) {
      set({ loading: false });
      throw e;
    }
  },

  verify2FA: async (username, password, code, method) => {
    set({ loading: true });
    try {
      const body: Record<string, string> = { username, password };
      if (method === "totp") {
        body.totp_code = code;
      } else {
        body.recovery_code = code;
      }
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Verification failed" }));
        throw new Error(err.detail || "Verification failed");
      }
      const data = await res.json();
      localStorage.setItem("istara_token", data.token);
      if (data.user?.id) localStorage.setItem("istara_auth_user_id", data.user.id);
      set({ user: data.user, token: data.token, loading: false });
      get().checkTeamStatus();
    } catch (e) {
      set({ loading: false });
      throw e;
    }
  },

  register: async (username, email, password, displayName) => {
    set({ loading: true });
    try {
      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password, display_name: displayName || username }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Registration failed" }));
        throw new Error(err.detail || "Registration failed");
      }
      const data = await res.json();
      localStorage.setItem("istara_token", data.token);
      if (data.user?.id) localStorage.setItem("istara_auth_user_id", data.user.id);
      set({ user: data.user, token: data.token, loading: false });
      get().checkTeamStatus();
    } catch (e) {
      set({ loading: false });
      throw e;
    }
  },

  logout: () => {
    localStorage.removeItem("istara_token");
    localStorage.removeItem("istara_auth_user_id");
    set({ user: null, token: null });
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  },

  checkTeamStatus: async () => {
    try {
      const _tk = localStorage.getItem("istara_token");
      const _hd: Record<string, string> = {};
      if (_tk) _hd["Authorization"] = `Bearer ${_tk}`;
      const res = await fetch(`${API_BASE}/api/auth/team-status`, { headers: _hd });
      const data = await res.json();
      const status = {
        team_mode: Boolean(data.team_mode),
        has_users: data.has_users !== false,
        insecure: Boolean(data.insecure),
      };
      set({
        teamMode: status.team_mode,
        hasUsers: status.has_users,
        insecure: status.insecure,
      });
      return status;
    } catch {
      const fallback = { team_mode: false, has_users: true, insecure: false };
      set({ teamMode: false, hasUsers: true, insecure: false });
      return fallback;
    }
  },

  fetchMe: async () => {
    const _tk = localStorage.getItem("istara_token");
    if (!_tk) return false;
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${_tk}` },
      });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem("istara_auth_user_id", data.id);
        set({
          user: {
            id: data.id,
            username: data.username,
            email: data.email || "",
            role: data.role,
            display_name: data.display_name || data.username,
            preferences: data.preferences || {},
          },
          teamMode: data.team_mode ?? get().teamMode,
        });
        return true;
      } else if (res.status === 401) {
        localStorage.removeItem("istara_token");
        localStorage.removeItem("istara_auth_user_id");
        set({ user: null, token: null });
        if (typeof window !== "undefined") {
          window.dispatchEvent(new Event("istara:auth-expired"));
        }
      }
    } catch {
      // Token invalid or server down — don't touch state
    }
    return false;
  },

  updatePreferences: async (prefs) => {
    const { token } = get();
    try {
      await fetch(`${API_BASE}/api/auth/preferences`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ preferences: prefs }),
      });
      const user = get().user;
      if (user) {
        set({ user: { ...user, preferences: { ...user.preferences, ...prefs } } });
      }
    } catch {
      // Ignore preference update errors
    }
  },

  getAuthHeaders: (): Record<string, string> => {
    const { token } = get();
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
    return {};
  },

  // --- Passkey / WebAuthn ---

  loginWithPasskey: async (username) => {
    set({ loading: true });
    try {
      const { startAuthentication } = await import("@simplewebauthn/browser");

      // 1. Start authentication
      const startRes = await fetch(`${API_BASE}/api/webauthn/authenticate/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username }),
      });
      if (!startRes.ok) {
        const err = await startRes.json().catch(() => ({ detail: "Passkey auth failed" }));
        throw new Error(err.detail || "Passkey auth failed");
      }
      const startData = await startRes.json();

      // 2. Browser authenticates
      const assertion = await startAuthentication({ optionsJSON: startData.publicKey });

      // 3. Finish authentication
      const finishRes = await fetch(`${API_BASE}/api/webauthn/authenticate/finish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: startData.user_id,
          id: assertion.id,
          raw_id: assertion.rawId,
          response_type: assertion.type,
          authenticator_data: assertion.response.authenticatorData,
          client_data_json: assertion.response.clientDataJSON,
          signature: assertion.response.signature,
          user_handle: assertion.response.userHandle,
        }),
      });
      if (!finishRes.ok) {
        const err = await finishRes.json().catch(() => ({ detail: "Passkey verification failed" }));
        throw new Error(err.detail || "Passkey verification failed");
      }
      const data = await finishRes.json();
      localStorage.setItem("istara_token", data.token);
      if (data.user?.id) localStorage.setItem("istara_auth_user_id", data.user.id);
      set({ user: data.user, token: data.token, loading: false });
      get().checkTeamStatus();
    } catch (e) {
      set({ loading: false });
      throw e;
    }
  },

  registerPasskey: async () => {
    set({ loading: true });
    try {
      const { startRegistration } = await import("@simplewebauthn/browser");
      const { user, token } = get();
      if (!user || !token) {
        throw new Error("You must be logged in to register a passkey");
      }

      // 1. Start registration
      const startRes = await fetch(`${API_BASE}/api/webauthn/register/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ username: user.username, display_name: user.display_name || user.username }),
      });
      if (!startRes.ok) {
        const err = await startRes.json().catch(() => ({ detail: "Passkey registration failed" }));
        throw new Error(err.detail || "Passkey registration failed");
      }
      const startData = await startRes.json();

      // 2. Browser creates credential
      const attestation = await startRegistration({ optionsJSON: startData.publicKey });

      // 3. Finish registration
      const finishRes = await fetch(`${API_BASE}/api/webauthn/register/finish`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_id: user.id,
          id: attestation.id,
          raw_id: attestation.rawId,
          response_type: attestation.type,
          authenticator_attachment: attestation.authenticatorAttachment,
          client_data_json: attestation.response.clientDataJSON,
          attestation_object: attestation.response.attestationObject,
          transports: attestation.response.transports || [],
        }),
      });
      if (!finishRes.ok) {
        const err = await finishRes.json().catch(() => ({ detail: "Passkey registration failed" }));
        throw new Error(err.detail || "Passkey registration failed");
      }
      set({ loading: false });
    } catch (e) {
      set({ loading: false });
      throw e;
    }
  },

  listPasskeys: async () => {
    const { token } = get();
    if (!token) throw new Error("Not authenticated");
    const res = await fetch(`${API_BASE}/api/webauthn/credentials`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to list passkeys" }));
      throw new Error(err.detail || "Failed to list passkeys");
    }
    return res.json();
  },

  deletePasskey: async (credentialId) => {
    const { token } = get();
    if (!token) throw new Error("Not authenticated");
    const res = await fetch(`${API_BASE}/api/webauthn/credentials/${credentialId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to delete passkey" }));
      throw new Error(err.detail || "Failed to delete passkey");
    }
  },
}));
