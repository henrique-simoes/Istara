"use client";

import { useEffect, useState } from "react";
import {
  FolderOpen,
  Plus,
  Diamond,
  Bot,
  Brain,
  LayoutDashboard,
  FileText,
  FileStack,
  Search,
  ChevronLeft,
  ChevronRight,
  Settings,
  History,
  BarChart3,
  Mic,
  MoreHorizontal,
  Wand2,
  Users,
  Server,
  Activity,
  Palette,
  RefreshCw,
  Bell,
  Archive,
  Sparkles,
  MessageSquare,
  FlaskConical,
  BookOpen,
  CheckCircle,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { useNotificationStore } from "@/stores/notificationStore";
import DarkModeToggle from "@/components/common/DarkModeToggle";
import UserMenu from "@/components/common/UserMenu";
import { cn, phaseLabel } from "@/lib/utils";

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
  onSearchOpen?: () => void;
}

function NotificationBell({ onViewChange }: { onViewChange: (view: string) => void }) {
  const { unreadCount, fetchUnreadCount } = useNotificationStore();

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30_000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  return (
    <button
      onClick={() => onViewChange("notifications")}
      className="relative p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 transition-colors focus:outline-none focus:ring-2 focus:ring-istara-500"
      aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ""}`}
      title="Notifications"
    >
      <Bell size={16} />
      {unreadCount > 0 && (
        <span
          className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[14px] h-[14px] px-0.5 text-[9px] font-bold text-white bg-red-600 rounded-full"
          aria-hidden="true"
        >
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      )}
    </button>
  );
}

export default function Sidebar({ activeView, onViewChange, onSearchOpen }: SidebarProps) {
  const {
    projects,
    activeProjectId,
    fetchProjects,
    setActiveProject,
    createProject,
    deleteProject,
    pauseProject,
    resumeProject,
  } = useProjectStore();
  const [collapsed, setCollapsed] = useState(false);
  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [showSecondary, setShowSecondary] = useState(false);
  const [projectMenu, setProjectMenu] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Auto-expand secondary nav when the active view is a secondary item
  useEffect(() => {
    const secondaryIds = ["autoresearch", "backup", "meta-hyperagent", "compute", "ensemble", "metrics", "history"];
    if (secondaryIds.includes(activeView)) {
      setShowSecondary(true);
    }
  }, [activeView]);

  const [createError, setCreateError] = useState<string | null>(null);

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;
    setCreateError(null);
    try {
      await createProject(newProjectName.trim());
      setNewProjectName("");
      setShowNewProject(false);
    } catch (e: any) {
      setCreateError(e.message || "Failed to create project");
      console.error("Project creation failed:", e);
    }
  };

  // Primary nav: 5 items (simplified from 8)
  const primaryNav = [
    { id: "chat", icon: Bot, label: "Chat" },
    { id: "findings", icon: Diamond, label: "Findings" },
    { id: "laws", icon: BookOpen, label: "UX Laws" },
    { id: "tasks", icon: LayoutDashboard, label: "Tasks" },
    { id: "interviews", icon: Mic, label: "Interviews" },
    { id: "documents", icon: FileStack, label: "Documents" },
    { id: "context", icon: FileText, label: "Context" },
    { id: "skills", icon: Wand2, label: "Skills" },
    { id: "agents", icon: Users, label: "Agents" },
    { id: "memory", icon: Brain, label: "Memory" },
    { id: "interfaces", icon: Palette, label: "Interfaces" },
    { id: "integrations", icon: MessageSquare, label: "Integrations" },
    { id: "loops", icon: RefreshCw, label: "Loops" },
    { id: "settings", icon: Settings, label: "Settings" },
  ];

  // Secondary nav: accessible via "More" or header icons
  const secondaryNav = [
    { id: "autoresearch", icon: FlaskConical, label: "Autoresearch" },
    { id: "backup", icon: Archive, label: "Backup" },
    { id: "meta-hyperagent", icon: Sparkles, label: "Meta-Agent" },
    { id: "compute", icon: Server, label: "Compute Pool" },
    { id: "ensemble", icon: Activity, label: "Ensemble Health" },
    { id: "quality", icon: CheckCircle, label: "Quality Dashboard" },
    { id: "project-settings", icon: Settings, label: "Project Settings" },
    { id: "history", icon: History, label: "History" },
  ];

  return (
    <aside
      role="navigation"
      aria-label="Main navigation"
      className={cn(
        "flex flex-col border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <span className="text-xl">🐾</span>
            <span className="font-bold text-lg text-slate-900 dark:text-white">Istara</span>
          </div>
        )}
        <div className="flex items-center gap-1">
          <NotificationBell onViewChange={onViewChange} />
          <DarkModeToggle />
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
      </div>

      {/* Scrollable content area — nav + projects share a single scroll container
           so opening "More" doesn't push projects off-screen */}
      <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
      {/* Search */}
      {onSearchOpen && (
        <button
          onClick={onSearchOpen}
          aria-label="Search findings (Cmd+K)"
          className={cn(
            "flex items-center gap-2 mx-2 mt-2 rounded-lg transition-colors shrink-0",
            collapsed
              ? "p-2 justify-center hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400"
              : "px-3 py-2 bg-slate-100 dark:bg-slate-800 text-slate-400 text-sm hover:bg-slate-200 dark:hover:bg-slate-700"
          )}
        >
          <Search size={14} />
          {!collapsed && (
            <>
              <span className="flex-1 text-left">Search...</span>
              <kbd className="text-[10px] bg-slate-200 dark:bg-slate-700 px-1 py-0.5 rounded">⌘K</kbd>
            </>
          )}
        </button>
      )}

      {/* Primary Navigation */}
      <nav className="p-2 space-y-0.5 shrink-0" aria-label="Views">
        <div role="tablist" aria-label="Main views">
          {primaryNav.map((item) => (
            <button
              key={item.id}
              onClick={() => onViewChange(item.id)}
              role="tab"
              aria-selected={activeView === item.id}
              aria-label={item.label}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors",
                activeView === item.id
                  ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              )}
            >
              <item.icon size={18} />
              {!collapsed && <span>{item.label}</span>}
            </button>
          ))}
        </div>

        {/* More toggle */}
        <button
          onClick={() => setShowSecondary(!showSecondary)}
          aria-label="More views"
          aria-expanded={showSecondary}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <MoreHorizontal size={18} />
          {!collapsed && <span>More</span>}
        </button>

        {/* Secondary nav (collapsible) */}
        {showSecondary && (
          <div role="tablist" aria-label="Secondary views">
            {secondaryNav.map((item) => (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                role="tab"
                aria-selected={activeView === item.id}
                aria-label={item.label}
                className={cn(
                  "flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors",
                  collapsed ? "" : "pl-6",
                  activeView === item.id
                    ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                    : "text-slate-500 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                )}
              >
                <item.icon size={16} />
                {!collapsed && <span>{item.label}</span>}
              </button>
            ))}
          </div>
        )}
      </nav>

      {/* Projects */}
      {!collapsed && (
        <div className="p-2 border-t border-slate-200 dark:border-slate-800 mt-1 shrink-0" tabIndex={0} role="region" aria-label="Projects list">
          <div className="flex items-center justify-between px-3 py-2">
            <span className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
              Projects
            </span>
            <button
              onClick={() => setShowNewProject(!showNewProject)}
              className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500"
              aria-label="Create new project"
            >
              <Plus size={14} />
            </button>
          </div>

          {showNewProject && (
            <div className="px-3 pb-2">
              <input
                type="text"
                placeholder="Project name..."
                value={newProjectName}
                onChange={(e) => { setNewProjectName(e.target.value); setCreateError(null); }}
                onKeyDown={(e) => e.key === "Enter" && handleCreateProject()}
                className="w-full px-2 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                aria-label="New project name"
                autoFocus
              />
              {createError && (
                <p className="text-xs text-red-500 mt-1 px-1">{createError}</p>
              )}
            </div>
          )}

          <div className="space-y-0.5" role="listbox" aria-label="Projects">
            {projects.map((project) => (
              <div key={project.id} className="relative group">
                <button
                  onClick={() => setActiveProject(project.id)}
                  onContextMenu={(e) => { e.preventDefault(); setProjectMenu(projectMenu === project.id ? null : project.id); }}
                  role="option"
                  aria-selected={activeProjectId === project.id}
                  className={cn(
                    "flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm transition-colors",
                    project.is_paused && "opacity-60",
                    activeProjectId === project.id
                      ? "bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white"
                      : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                  )}
                >
                  <FolderOpen size={14} className="shrink-0" />
                  <div className="text-left truncate flex-1 min-w-0">
                    <div className="truncate">{project.name}</div>
                    <div className="text-xs text-slate-400">
                      {project.is_paused ? "⏸ Paused" : phaseLabel(project.phase)}
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setProjectMenu(projectMenu === project.id ? null : project.id); }}
                    className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 shrink-0"
                    aria-label="Project options"
                  >
                    <MoreHorizontal size={12} />
                  </button>
                </button>
                {projectMenu === project.id && (
                  <div className="absolute left-8 top-full mt-1 z-50 w-36 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1 text-xs">
                    <button
                      onClick={() => { project.is_paused ? resumeProject(project.id) : pauseProject(project.id); setProjectMenu(null); }}
                      className="w-full text-left px-3 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300"
                    >
                      {project.is_paused ? "Resume" : "Pause"}
                    </button>
                    <button
                      onClick={() => { if (window.confirm(`Delete "${project.name}"?`)) { deleteProject(project.id); } setProjectMenu(null); }}
                      className="w-full text-left px-3 py-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400"
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {projects.length === 0 && (
            <p className="px-3 py-4 text-sm text-slate-400 text-center">
              No projects yet. Create one to get started.
            </p>
          )}
        </div>
      )}

      </div>{/* end scrollable content area */}

      {/* User Menu */}
      <UserMenu collapsed={collapsed} />
    </aside>
  );
}
