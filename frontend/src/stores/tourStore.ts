/** Guided onboarding tour state — manages step progression, conditional logic, and persistence. */

import { create } from "zustand";

const STORAGE_KEY = "istara_tour_state";
const COMPLETED_KEY = "istara_tour_completed";

/** Total number of logical steps (some may be skipped based on role/context). */
export const TOUR_TOTAL_STEPS = 10;

/** Steps that only admins see (team management). */
const ADMIN_ONLY_STEPS = new Set([2, 3, 4]);

/** Steps that require no project to exist yet (project setup). */
const PROJECT_SETUP_STEPS = new Set([0, 1]);

/** Steps conditional on team mode being enabled. */
const TEAM_ENABLED_STEPS = new Set([3, 4]);

export interface TourState {
  active: boolean;
  step: number;
  folderPath: string;
  createdProjectId: string;
  role: "admin" | "researcher" | "viewer";
  hasExistingProjects: boolean;
  teamModeEnabled: boolean;
  connectionStringGenerated: boolean;
  llmConnected: boolean;
  llmProvider: string;
  llmModel: string;

  startTour: (role: string, hasProjects: boolean) => void;
  nextStep: () => void;
  goToStep: (step: number) => void;
  skipTour: () => void;
  completeTour: () => void;
  setFolderPath: (path: string) => void;
  setProjectCreated: (id: string) => void;
  setTeamModeEnabled: (v: boolean) => void;
  setConnectionStringGenerated: () => void;
  setLlmStatus: (connected: boolean, provider?: string, model?: string) => void;
}

function resolveNextStep(
  current: number,
  role: string,
  hasProjects: boolean,
  teamModeEnabled: boolean,
): number {
  let next = current + 1;
  while (next < TOUR_TOTAL_STEPS) {
    // Skip project setup if projects already exist
    if (PROJECT_SETUP_STEPS.has(next) && hasProjects) {
      next++;
      continue;
    }
    // Skip admin-only steps if not admin
    if (ADMIN_ONLY_STEPS.has(next) && role !== "admin") {
      next++;
      continue;
    }
    // Skip team-dependent steps if team mode not enabled
    if (TEAM_ENABLED_STEPS.has(next) && !teamModeEnabled) {
      next++;
      continue;
    }
    break;
  }
  return next;
}

function resolveFirstStep(role: string, hasProjects: boolean): number {
  if (hasProjects) {
    // Skip project setup entirely
    if (role === "admin") return 2; // Team mode
    return 5; // Members skip to files
  }
  return 0; // Start from scratch
}

function loadPersistedState(): Partial<TourState> | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return null;
}

function persistState(state: Partial<TourState>) {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        active: state.active,
        step: state.step,
        folderPath: state.folderPath,
        createdProjectId: state.createdProjectId,
        role: state.role,
        hasExistingProjects: state.hasExistingProjects,
        teamModeEnabled: state.teamModeEnabled,
        connectionStringGenerated: state.connectionStringGenerated,
      }),
    );
  } catch {}
}

export function isTourCompleted(): boolean {
  try {
    return localStorage.getItem(COMPLETED_KEY) === "true";
  } catch {
    return false;
  }
}

export const useTourStore = create<TourState>((set, get) => {
  const persisted = loadPersistedState();

  return {
    active: persisted?.active ?? false,
    step: persisted?.step ?? 0,
    folderPath: persisted?.folderPath ?? "",
    createdProjectId: persisted?.createdProjectId ?? "",
    role: (persisted?.role as TourState["role"]) ?? "admin",
    hasExistingProjects: persisted?.hasExistingProjects ?? false,
    teamModeEnabled: persisted?.teamModeEnabled ?? false,
    connectionStringGenerated: persisted?.connectionStringGenerated ?? false,
    llmConnected: false,
    llmProvider: "",
    llmModel: "",

    startTour: (role, hasProjects) => {
      const r = (role === "admin" ? "admin" : role === "viewer" ? "viewer" : "researcher") as TourState["role"];
      const firstStep = resolveFirstStep(r, hasProjects);
      const state = {
        active: true,
        step: firstStep,
        folderPath: "",
        createdProjectId: "",
        role: r,
        hasExistingProjects: hasProjects,
        teamModeEnabled: false,
        connectionStringGenerated: false,
        llmConnected: false,
        llmProvider: "",
        llmModel: "",
      };
      set(state);
      persistState(state);
    },

    nextStep: () => {
      const s = get();
      const next = resolveNextStep(s.step, s.role, s.hasExistingProjects, s.teamModeEnabled);
      if (next >= TOUR_TOTAL_STEPS) {
        get().completeTour();
        return;
      }
      set({ step: next });
      persistState({ ...s, step: next });
    },

    goToStep: (step) => {
      const s = get();
      set({ step });
      persistState({ ...s, step });
    },

    skipTour: () => {
      set({ active: false, step: 0 });
      try {
        localStorage.setItem(COMPLETED_KEY, "true");
        localStorage.removeItem(STORAGE_KEY);
      } catch {}
    },

    completeTour: () => {
      set({ active: false, step: 0 });
      try {
        localStorage.setItem(COMPLETED_KEY, "true");
        localStorage.removeItem(STORAGE_KEY);
      } catch {}
    },

    setFolderPath: (path) => {
      const s = get();
      set({ folderPath: path });
      persistState({ ...s, folderPath: path });
    },

    setProjectCreated: (id) => {
      const s = get();
      set({ createdProjectId: id, hasExistingProjects: true });
      persistState({ ...s, createdProjectId: id, hasExistingProjects: true });
    },

    setTeamModeEnabled: (v) => {
      const s = get();
      set({ teamModeEnabled: v });
      persistState({ ...s, teamModeEnabled: v });
    },

    setConnectionStringGenerated: () => {
      const s = get();
      set({ connectionStringGenerated: true });
      persistState({ ...s, connectionStringGenerated: true });
    },

    setLlmStatus: (connected, provider, model) => {
      set({ llmConnected: connected, llmProvider: provider || "", llmModel: model || "" });
    },
  };
});
