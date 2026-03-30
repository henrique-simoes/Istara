"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/layout/Sidebar";
import RightPanel from "@/components/layout/RightPanel";
import StatusBar from "@/components/layout/StatusBar";
import ChatView from "@/components/chat/ChatView";
import KanbanBoard from "@/components/kanban/KanbanBoard";
import FindingsView from "@/components/findings/FindingsView";
import InterviewView from "@/components/interviews/InterviewView";
import MetricsView from "@/components/metrics/MetricsView";
import ContextEditor from "@/components/projects/ContextEditor";
import VersionHistory from "@/components/common/VersionHistory";
import SettingsView from "@/components/common/SettingsView";
import ComputePoolView from "@/components/common/ComputePoolView";
import EnsembleHealthView from "@/components/common/EnsembleHealthView";
import SkillsView from "@/components/skills/SkillsView";
import AgentsView from "@/components/agents/AgentsView";
import MemoryView from "@/components/memory/MemoryView";
import InterfacesView from "@/components/interfaces/InterfacesView";
import IntegrationsView from "@/components/integrations/IntegrationsView";
import LoopsView from "@/components/loops/LoopsView";
import NotificationsView from "@/components/notifications/NotificationsView";
import BackupView from "@/components/backup/BackupView";
import MetaHyperagentView from "@/components/meta/MetaHyperagentView";
import AutoresearchView from "@/components/autoresearch/AutoresearchView";
import LawsView from "@/components/laws/LawsView";
import DocumentsView from "@/components/documents/DocumentsView";
import SearchModal from "@/components/common/SearchModal";
import ToastNotification from "@/components/common/ToastNotification";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import KeyboardShortcuts from "@/components/common/KeyboardShortcuts";
import MobileNav from "@/components/layout/MobileNav";
import OnboardingWizard from "@/components/onboarding/OnboardingWizard";
import LoginScreen from "@/components/auth/LoginScreen";
import { useProjectStore } from "@/stores/projectStore";
import { useAuthStore } from "@/stores/authStore";
import { useSessionStore } from "@/stores/sessionStore";
import { useAgentStore } from "@/stores/agentStore";
import { settings as settingsApi } from "@/lib/api";

const VIEW_STORAGE_KEY = "istara_active_view";
const VIEW_NAMES: Record<string, string> = {
  chat: "Chat", findings: "Findings", tasks: "Tasks", laws: "UX Laws",
  interviews: "Interviews", documents: "Documents", metrics: "Metrics",
  context: "Context", skills: "Skills", agents: "Agents", memory: "Memory",
  interfaces: "Interfaces", integrations: "Integrations", loops: "Loops",
  notifications: "Notifications", backup: "Backup", "meta-hyperagent": "Meta-Agent",
  autoresearch: "AutoResearch", history: "History", compute: "Compute Pool",
  ensemble: "Ensemble Health", settings: "Settings",
};

function getSavedView(): string {
  if (typeof window === "undefined") return "chat";
  try { return localStorage.getItem(VIEW_STORAGE_KEY) || "chat"; } catch { return "chat"; }
}

export default function HomeClient() {
  const [activeView, setActiveViewRaw] = useState(getSavedView);
  const setActiveView = (view: string) => {
    setActiveViewRaw(view);
    try { localStorage.setItem(VIEW_STORAGE_KEY, view); } catch {}
    document.title = `${VIEW_NAMES[view] || "Istara"} — Istara`;
  };
  // Set title on mount
  useEffect(() => { document.title = `${VIEW_NAMES[activeView] || "Istara"} — Istara`; }, []);

  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const { projects, activeProjectId, fetchProjects } = useProjectStore();

  // Check authentication on mount
  useEffect(() => {
    const token = localStorage.getItem("istara_token");
    if (!token || token === "local-mode") {
      setAuthenticated(false);
      return;
    }
    // Token exists — assume valid (middleware will reject if expired)
    setAuthenticated(true);
    // Restore user object from JWT + check team mode status
    useAuthStore.getState().fetchMe();
    useAuthStore.getState().checkTeamStatus();

    // Listen for token expiry events from API client
    const handleExpiry = () => setAuthenticated(false);
    window.addEventListener("istara:auth-expired", handleExpiry);
    return () => window.removeEventListener("istara:auth-expired", handleExpiry);
  }, []);

  // Check if first-run (no projects) — only after authenticated
  useEffect(() => {
    if (!authenticated) return;
    fetchProjects().then(() => {
      const store = useProjectStore.getState();
      if (store.projects.length === 0) {
        setShowOnboarding(true);
      }
    });
  }, [fetchProjects]);

  // Handle istara:navigate events from AgentsView, ToastNotification, etc.
  useEffect(() => {
    const handler = async (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (typeof detail === "string") {
        setActiveView(detail);
      } else if (detail?.view) {
        setActiveView(detail.view);
        // If navigating to chat with a specific agent, create/find a session for that agent
        if (detail.view === "chat") {
          const { sessions, createSession, selectSession, setPendingPrefill } = useSessionStore.getState();
          const { activeProjectId } = useProjectStore.getState();
          if (activeProjectId) {
            if (detail.agent_id) {
              const existing = sessions.find((s) => s.agent_id === detail.agent_id);
              if (existing) {
                selectSession(existing.id);
              } else {
                const agents = useAgentStore.getState().agents;
                const agent = agents.find((a) => a.id === detail.agent_id);
                await createSession(activeProjectId, `Chat with ${agent?.name || "Agent"}`, detail.agent_id);
              }
            }
            // If a prefill message was provided (e.g. from "Send to Agent"), queue it
            if (detail.prefill) {
              setPendingPrefill(detail.prefill);
            }
          }
        }
      }
    };
    window.addEventListener("istara:navigate", handler);
    return () => window.removeEventListener("istara:navigate", handler);
  }, []);

  // Global Cmd+K for search
  useEffect(() => {
    const viewKeys: Record<string, string> = { "1": "chat", "2": "findings", "3": "tasks", "4": "interviews", "5": "documents", "6": "context", "7": "skills", "8": "agents", "9": "memory", "0": "interfaces" };

    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
      // ⌘1-5 for view switching
      if ((e.metaKey || e.ctrlKey) && viewKeys[e.key]) {
        e.preventDefault();
        setActiveView(viewKeys[e.key]);
      }
      // ⌘. toggle right panel
      if ((e.metaKey || e.ctrlKey) && e.key === ".") {
        e.preventDefault();
        setRightPanelCollapsed((prev) => !prev);
      }
      // ? for shortcut help (when not typing)
      if (e.key === "?" && !["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)) {
        setShortcutsOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Show login screen if not authenticated
  if (authenticated === null) return null; // Loading state
  if (authenticated === false) {
    return <LoginScreen onLogin={() => setAuthenticated(true)} />;
  }

  // Views that require an active project to show meaningful content
  const PROJECT_REQUIRED_VIEWS = new Set([
    "chat", "tasks", "findings", "laws", "interviews", "documents",
    "metrics", "context", "loops", "memory", "history", "interfaces",
    "autoresearch", "backup",
  ]);

  const renderView = () => {
    // Guard: views that need a project show a prompt when none is selected
    if (PROJECT_REQUIRED_VIEWS.has(activeView) && !activeProjectId) {
      return (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center max-w-sm">
            <div className="text-4xl mb-3">📂</div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">No Project Selected</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
              Create or select a project in the sidebar to use {VIEW_NAMES[activeView] || "this view"}.
            </p>
          </div>
        </div>
      );
    }

    switch (activeView) {
      case "chat": return <ChatView />;
      case "tasks": return <KanbanBoard />;
      case "findings": return <FindingsView />;
      case "laws": return <LawsView />;
      case "interviews": return <InterviewView />;
      case "documents": return <DocumentsView />;
      case "metrics": return <MetricsView />;
      case "context": return <ContextEditor />;
      case "skills": return <SkillsView />;
      case "agents": return <AgentsView />;
      case "memory": return <MemoryView />;
      case "interfaces": return <InterfacesView />;
      case "integrations": return <IntegrationsView />;
      case "loops": return <LoopsView />;
      case "notifications": return <NotificationsView />;
      case "backup": return <BackupView />;
      case "meta-hyperagent": return <MetaHyperagentView />;
      case "autoresearch": return <AutoresearchView />;
      case "history": return <VersionHistory />;
      case "compute": return <ComputePoolView />;
      case "ensemble": return <EnsembleHealthView />;
      case "settings": return <SettingsView />;
      default: return <ChatView />;
    }
  };

  return (
    <div className="h-screen flex flex-col">
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar: hidden on mobile, visible on lg+ */}
        <div className="hidden lg:flex">
          <Sidebar
            activeView={activeView}
            onViewChange={setActiveView}
            onSearchOpen={() => setSearchOpen(true)}
          />
        </div>
        <main className="flex-1 flex flex-col overflow-hidden pb-14 lg:pb-0" id="main-content">
          <ErrorBoundary>
            {renderView()}
          </ErrorBoundary>
        </main>
        {/* Right panel: hidden on mobile */}
        <div className="hidden xl:flex">
          <RightPanel
            activeView={activeView}
            collapsed={rightPanelCollapsed}
            onToggle={() => setRightPanelCollapsed(!rightPanelCollapsed)}
          />
        </div>
      </div>
      <div className="hidden lg:block">
        <StatusBar />
      </div>
      <MobileNav activeView={activeView} onViewChange={setActiveView} />
      <ToastNotification />
      <SearchModal open={searchOpen} onClose={() => setSearchOpen(false)} onNavigate={setActiveView} />
      <KeyboardShortcuts open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
      {showOnboarding && (
        <OnboardingWizard onComplete={() => setShowOnboarding(false)} />
      )}
    </div>
  );
}
