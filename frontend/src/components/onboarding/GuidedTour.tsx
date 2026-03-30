"use client";

import { useEffect, useCallback, useRef, useState } from "react";
import { useTourStore, TOUR_TOTAL_STEPS } from "@/stores/tourStore";
import { settings as settingsApi } from "@/lib/api";
import TourPopover from "./TourPopover";
import TourInlineStep from "./TourInlineStep";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface GuidedTourProps {
  setActiveView: (view: string) => void;
  currentView: string;
}

/** Step definitions for the guided tour. */
interface StepDef {
  view: string | null; // null = inline step (no view navigation)
  targetSelector: string | null;
  placement: "top" | "bottom" | "left" | "right";
  title: string;
  getDescription: (tour: ReturnType<typeof useTourStore.getState>) => React.ReactNode;
  getActions: (
    tour: ReturnType<typeof useTourStore.getState>,
    extra: { llmConnected: boolean; llmProvider: string; llmModel: string },
  ) => { label: string; onClick: () => void; variant?: "primary" | "secondary" | "ghost" }[];
  spotlight?: boolean;
}

const STEPS: StepDef[] = [
  // Step 0: Welcome + Folder — rendered by TourInlineStep
  {
    view: null,
    targetSelector: null,
    placement: "bottom",
    title: "Welcome",
    getDescription: () => "",
    getActions: () => [],
  },
  // Step 1: Create Project — rendered by TourInlineStep
  {
    view: null,
    targetSelector: null,
    placement: "bottom",
    title: "Create Project",
    getDescription: () => "",
    getActions: () => [],
  },
  // Step 2: Team Mode
  {
    view: "settings",
    targetSelector: "#tour-target-team-mode",
    placement: "bottom",
    title: "Invite Your Team",
    getDescription: () => (
      <p>
        Enable <strong>Team Mode</strong> to let others collaborate on your research.
        Toggle it on, or skip this for solo use.
      </p>
    ),
    getActions: (tour) => [
      { label: "Next", onClick: () => tour.nextStep(), variant: "primary" },
    ],
    spotlight: true,
  },
  // Step 3: Invite Members (conditional — team mode on)
  {
    view: "settings",
    targetSelector: "#tour-target-user-management",
    placement: "bottom",
    title: "Invite Team Members",
    getDescription: () => (
      <p>
        Create accounts for your team here, or use <strong>Connection Strings</strong> below
        for self-service invites. Team members paste the string on the login screen.
      </p>
    ),
    getActions: (tour) => [
      { label: "Next", onClick: () => tour.nextStep(), variant: "primary" },
    ],
    spotlight: true,
  },
  // Step 4: Connection String (conditional — team mode on)
  {
    view: "settings",
    targetSelector: "#tour-target-connection-strings",
    placement: "top",
    title: "Share a Connection String",
    getDescription: (tour) =>
      tour.connectionStringGenerated ? (
        <p className="text-green-700 dark:text-green-400 font-medium">
          Connection string generated! Share it with your team members — they paste it on the login screen to join instantly.
        </p>
      ) : (
        <p>
          Generate a <strong>Connection String</strong> and share it with team members.
          Choose a label (e.g. "Alice's laptop") and an expiry time, then click Generate.
        </p>
      ),
    getActions: (tour) => [
      { label: "Next", onClick: () => tour.nextStep(), variant: "primary" },
    ],
    spotlight: true,
  },
  // Step 5: Add Files
  {
    view: null, // stays on current view
    targetSelector: null, // centered popover
    placement: "bottom",
    title: "Add Your Research Files",
    getDescription: (tour) => (
      <div>
        <p>
          Put your research files (transcripts, surveys, reports, spreadsheets) in your project folder:
        </p>
        {tour.folderPath && (
          <code className="block mt-2 px-3 py-1.5 rounded bg-slate-100 dark:bg-slate-800 text-xs font-mono text-slate-700 dark:text-slate-300 truncate">
            {tour.folderPath}
          </code>
        )}
        <p className="mt-2 text-xs text-slate-400">
          Istara will automatically detect and index new files. You can also upload files directly in the Documents view.
        </p>
      </div>
    ),
    getActions: (tour) => [
      { label: "Next", onClick: () => tour.nextStep(), variant: "primary" },
    ],
  },
  // Step 6: Project Context
  {
    view: "context",
    targetSelector: "#tour-target-context-editor",
    placement: "top",
    title: "Set Your Research Context",
    getDescription: (tour) =>
      tour.role !== "admin" ? (
        <p>
          Review the project context your admin set up. You can update the company info,
          project goals, and guardrails to help Istara understand your research better.
        </p>
      ) : (
        <p>
          Tell Istara about your company and project. This context helps agents provide
          relevant analysis, ask better questions, and produce insights that fit your domain.
        </p>
      ),
    getActions: (tour) => [
      { label: "Done", onClick: () => tour.nextStep(), variant: "primary" },
    ],
    spotlight: true,
  },
  // Step 7: Tasks
  {
    view: "tasks",
    targetSelector: "#tour-target-kanban",
    placement: "top",
    title: "Your Research Task Board",
    getDescription: (tour) =>
      tour.role !== "admin" ? (
        <p>
          Check the task board for work assigned to you. Your admin may have created tasks.
          You can also create your own and assign AI agents to help.
        </p>
      ) : (
        <p>
          Create research tasks and assign them to AI agents. Istara will work on them
          autonomously — analyzing data, generating insights, and updating progress.
        </p>
      ),
    getActions: (tour) => [
      { label: "Next", onClick: () => tour.nextStep(), variant: "primary" },
    ],
    spotlight: true,
  },
  // Step 8: LLM Model Check
  {
    view: "settings",
    targetSelector: "#tour-target-system-status",
    placement: "bottom",
    title: "Connect Your AI Model",
    getDescription: (_tour, extra) =>
      extra.llmConnected ? (
        <div>
          <p className="text-green-700 dark:text-green-400 font-medium mb-1">
            LLM connected! Model: <code className="font-mono">{extra.llmModel || "unknown"}</code>
          </p>
          <p>You're all set to start researching with AI assistance.</p>
        </div>
      ) : (
        <div>
          <p className="mb-2">
            Make sure <strong>LM Studio</strong> or <strong>Ollama</strong> is running with a model loaded.
          </p>
          <ul className="list-disc list-inside text-xs space-y-1 text-slate-500 dark:text-slate-400">
            <li>Check the <strong>Recommended Model</strong> section below for what fits your hardware</li>
            <li>Use <strong>Available Models</strong> to load a model directly</li>
            <li>Or open LM Studio / Ollama and load a model there</li>
          </ul>
          <p className="mt-2 text-xs text-amber-600 dark:text-amber-400 animate-pulse">
            Waiting for LLM connection...
          </p>
        </div>
      ),
    getActions: (_tour, extra) =>
      extra.llmConnected
        ? [{ label: "Start Chatting →", onClick: () => _tour.nextStep(), variant: "primary" as const }]
        : [],
    spotlight: true,
  },
  // Step 9: Chat — final step
  {
    view: "chat",
    targetSelector: null,
    placement: "bottom",
    title: "You're Ready!",
    getDescription: () => (
      <div>
        <p className="mb-2">
          Start chatting with Istara about your research. Try:
        </p>
        <ul className="list-disc list-inside text-xs space-y-1 text-slate-500 dark:text-slate-400">
          <li>"Analyze the documents in my project"</li>
          <li>"Create a research plan for user interviews"</li>
          <li>"What themes emerge from my data?"</li>
        </ul>
      </div>
    ),
    getActions: (tour) => [
      { label: "Got it!", onClick: () => tour.completeTour(), variant: "primary" },
    ],
  },
];

export default function GuidedTour({ setActiveView, currentView }: GuidedTourProps) {
  const tour = useTourStore();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [showResume, setShowResume] = useState(false);
  const autoDismissRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const step = tour.step;
  const stepDef = STEPS[step] || null;

  // Navigate to the correct view when step changes
  useEffect(() => {
    if (!tour.active || !stepDef) return;
    if (stepDef.view && stepDef.view !== currentView) {
      setActiveView(stepDef.view);
    }
  }, [tour.active, step, stepDef, currentView, setActiveView]);

  // Show "Resume Tour" if user navigates away from tour's target view
  useEffect(() => {
    if (!tour.active || !stepDef?.view) {
      setShowResume(false);
      return;
    }
    setShowResume(stepDef.view !== currentView);
  }, [tour.active, stepDef, currentView]);

  // Listen for custom events from settings components
  useEffect(() => {
    const handleTeamToggle = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      tour.setTeamModeEnabled(detail?.enabled ?? false);
    };
    const handleConnString = () => {
      tour.setConnectionStringGenerated();
    };

    window.addEventListener("istara:team-mode-toggled", handleTeamToggle);
    window.addEventListener("istara:connection-string-generated", handleConnString);
    return () => {
      window.removeEventListener("istara:team-mode-toggled", handleTeamToggle);
      window.removeEventListener("istara:connection-string-generated", handleConnString);
    };
  }, [tour]);

  // Poll LLM status on step 8
  useEffect(() => {
    if (!tour.active || step !== 8) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }

    const checkLLM = async () => {
      try {
        const status = await settingsApi.status();
        const connected = status?.services?.llm === "connected";
        const provider = status?.provider || "";
        const model = status?.config?.model || "";
        tour.setLlmStatus(connected, provider, model);
      } catch {}
    };

    checkLLM();
    pollRef.current = setInterval(checkLLM, 3000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [tour.active, step]);

  // Auto-dismiss final step after 10 seconds
  useEffect(() => {
    if (tour.active && step === 9) {
      autoDismissRef.current = setTimeout(() => tour.completeTour(), 10000);
    }
    return () => {
      if (autoDismissRef.current) clearTimeout(autoDismissRef.current);
    };
  }, [tour.active, step]);

  // Not active — nothing to render
  if (!tour.active) return null;

  // Steps 0-1: inline full-screen cards
  if (step <= 1) {
    return <TourInlineStep step={step} />;
  }

  // Steps 2+: floating popover on real views

  // Count visible steps for progress display
  const visibleSteps = STEPS.filter((_, i) => {
    if (tour.hasExistingProjects && i <= 1) return false;
    if (tour.role !== "admin" && [2, 3, 4].includes(i)) return false;
    if (!tour.teamModeEnabled && [3, 4].includes(i)) return false;
    return true;
  }).length;

  const visibleIndex = STEPS.slice(0, step + 1).filter((_, i) => {
    if (tour.hasExistingProjects && i <= 1) return false;
    if (tour.role !== "admin" && [2, 3, 4].includes(i)) return false;
    if (!tour.teamModeEnabled && [3, 4].includes(i)) return false;
    return true;
  }).length - 1;

  // "Resume Tour" pill
  if (showResume) {
    return (
      <button
        onClick={() => {
          if (stepDef?.view) setActiveView(stepDef.view);
          setShowResume(false);
        }}
        className="fixed bottom-6 right-6 z-[999] px-4 py-2 rounded-full bg-istara-600 text-white text-sm font-medium shadow-lg hover:bg-istara-700 transition animate-bounce"
        aria-label="Resume onboarding tour"
      >
        🐾 Resume Tour
      </button>
    );
  }

  if (!stepDef) return null;

  return (
    <TourPopover
      targetSelector={stepDef.targetSelector}
      placement={stepDef.placement}
      title={stepDef.title}
      description={stepDef.getDescription(tour, {
        llmConnected: tour.llmConnected,
        llmProvider: tour.llmProvider,
        llmModel: tour.llmModel,
      })}
      actions={stepDef.getActions(tour, {
        llmConnected: tour.llmConnected,
        llmProvider: tour.llmProvider,
        llmModel: tour.llmModel,
      })}
      stepNumber={visibleIndex}
      totalSteps={visibleSteps}
      onSkip={tour.skipTour}
      spotlight={stepDef.spotlight}
    />
  );
}
