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

interface AuthState {
  user: User | null;
  token: string | null;
  teamMode: boolean;
  loading: boolean;

  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
  checkTeamStatus: () => Promise<void>;
  updatePreferences: (prefs: Record<string, unknown>) => Promise<void>;
  getAuthHeaders: () => Record<string, string>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: typeof window !== "undefined" ? localStorage.getItem("reclaw_token") : null,
  teamMode: false,
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
      localStorage.setItem("reclaw_token", data.token);
      set({ user: data.user, token: data.token, loading: false });
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
      localStorage.setItem("reclaw_token", data.token);
      set({ user: data.user, token: data.token, loading: false });
    } catch (e) {
      set({ loading: false });
      throw e;
    }
  },

  logout: () => {
    localStorage.removeItem("reclaw_token");
    set({ user: null, token: null });
  },

  checkTeamStatus: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/team-status`);
      const data = await res.json();
      set({ teamMode: data.team_mode });
    } catch {
      set({ teamMode: false });
    }
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
    if (token && token !== "local-mode") {
      return { Authorization: `Bearer ${token}` };
    }
    return {} as Record<string, string>;
  },
}));
