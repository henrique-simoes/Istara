"use client";

import { useEffect, useState } from "react";
import {
  FolderOpen,
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
  MoreHorizontal,
  Bell,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { useNotificationStore } from "@/stores/notificationStore";
import { useAuthStore } from "@/stores/authStore";
import type { Project } from "@/lib/types";
import DarkModeToggle from "@/components/common/DarkModeToggle";
import UserMenu from "@/components/common/UserMenu";
import { cn, phaseLabel, agentEngineLabel } from "@/lib/utils";
import {
  SECONDARY_NAV_IDS,
  SECONDARY_NAV_ITEMS,
  filterNavItemsForRole,
  primaryNavItemsForRole,
  type ViewId,
} from "@/lib/navigation";

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
  onSearchOpen?: () => void;
}

function NotificationBell({ onViewChange }: { onViewChange: (view: string) => void }) {
  const { unreadCount, fetchUnreadCount } = useNotificationStore();
  const { activeProjectId } = useProjectStore();

  useEffect(() => {
    fetchUnreadCount(activeProjectId);
    const interval = setInterval(() => fetchUnreadCount(activeProjectId), 30_000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount, activeProjectId]);

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

function SidebarHeader({ collapsed, onToggle, onViewChange }: {
  collapsed: boolean;
  onToggle: () => void;
  onViewChange: (view: string) => void;
}) {
  return (
    <div
      className={cn(
        "flex border-b border-slate-200 dark:border-slate-800",
        collapsed ? "flex-col items-center gap-2 p-2" : "items-center justify-between p-4"
      )}
    >
      {!collapsed && (
        <div className="flex items-center gap-2">
          <span className="text-xl">🐾</span>
          <span className="font-bold text-lg text-slate-900 dark:text-white">Istara</span>
        </div>
      )}
      <div className={cn("flex items-center gap-1", collapsed && "flex-col")}>
        <NotificationBell onViewChange={onViewChange} />
        <DarkModeToggle />
        <button
          onClick={onToggle}
          className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>
    </div>
  );
}

function SearchControl({ collapsed, onSearchOpen }: { collapsed: boolean; onSearchOpen?: () => void }) {
  if (!onSearchOpen) return null;
  return (
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
  );
}

function ViewNavigation({ activeView, onViewChange, collapsed, showSecondary, onToggleSecondary, role }: {
  activeView: string;
  onViewChange: (view: string) => void;
  collapsed: boolean;
  showSecondary: boolean;
  onToggleSecondary: () => void;
  role?: string | null;
}) {
  const primaryNav = primaryNavItemsForRole(role);
  const secondaryNav = filterNavItemsForRole(SECONDARY_NAV_ITEMS, role);
  const navClass = "flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors";
  return (
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
              navClass,
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
      <button
        onClick={onToggleSecondary}
        aria-label="More views"
        aria-expanded={showSecondary}
        className={`${navClass} text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800`}
      >
        <MoreHorizontal size={18} />
        {!collapsed && <span>More</span>}
      </button>
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
                navClass,
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
  );
}

function NewProjectForm({ value, onChange, onSubmit, error }: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  error: string | null;
}) {
  return (
    <div className="px-3 pb-2">
      <input
        type="text"
        placeholder="Project name..."
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => event.key === "Enter" && onSubmit()}
        className="w-full px-2 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
        aria-label="New project name"
        autoFocus
      />
      {error && <p className="text-xs text-red-500 mt-1 px-1">{error}</p>}
    </div>
  );
}

function ProjectRow({ project, activeProjectId, menuOpen, onSelect, onToggleMenu, onPause, onResume, onDelete }: {
  project: Project;
  activeProjectId: string | null;
  menuOpen: boolean;
  onSelect: () => void;
  onToggleMenu: () => void;
  onPause: () => void;
  onResume: () => void;
  onDelete: () => void;
}) {
  const active = activeProjectId === project.id;
  const engine = agentEngineLabel(project.agentic_engine || project.global_agentic_engine);
  const engineClass = engine === "Pi"
    ? "bg-istara-100 text-istara-700 dark:bg-istara-900/40 dark:text-istara-400"
    : "bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-slate-400";
  return (
    <div className="relative group flex items-center">
      <button
        type="button"
        onClick={onSelect}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onSelect();
          }
        }}
        onContextMenu={(event) => { event.preventDefault(); onToggleMenu(); }}
        aria-current={activeProjectId === project.id ? "page" : undefined}
        className={cn(
          "cursor-pointer",
          "flex min-w-0 flex-1 items-center gap-2 rounded-lg px-3 py-2 pr-8 text-left text-sm transition-colors",
          project.is_paused && "opacity-60",
          active
            ? "bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white"
            : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
        )}
      >
        <FolderOpen size={14} className="shrink-0" />
        <div className="text-left truncate flex-1 min-w-0">
          <div className="truncate">{project.name}</div>
          <div className="text-xs text-slate-400 flex items-center gap-1">
            <span className="truncate">{project.is_paused ? "⏸ Paused" : phaseLabel(project.phase)}</span>
            <span
              aria-label={`Engine: ${engine}`}
              title={`Agent engine: ${engine}${project.agentic_engine ? "" : " (global default)"}`}
              className={cn("shrink-0 px-1 rounded text-[9px] font-semibold uppercase tracking-wide", engineClass)}
            >
              {engine}
            </span>
          </div>
        </div>
      </button>
      <button
        type="button"
        onClick={(event) => { event.stopPropagation(); onToggleMenu(); }}
        className="absolute right-2 rounded p-0.5 text-slate-400 opacity-0 hover:bg-slate-200 group-hover:opacity-100 dark:hover:bg-slate-700"
        aria-label="Project options"
      >
        <MoreHorizontal size={12} />
      </button>
      {menuOpen && (
        <div className="absolute left-8 top-full mt-1 z-50 w-36 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1 text-xs">
          <button
            onClick={project.is_paused ? onResume : onPause}
            className="w-full text-left px-3 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300"
          >
            {project.is_paused ? "Resume" : "Pause"}
          </button>
          <button
            onClick={onDelete}
            className="w-full text-left px-3 py-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400"
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

function ProjectsSection({ collapsed, projects, activeProjectId, showNewProject, onToggleNewProject, newProjectName, onNameChange, onCreate, createError, projectMenu, onToggleMenu, onSelectProject, onPause, onResume, onDelete }: {
  collapsed: boolean;
  projects: Project[];
  activeProjectId: string | null;
  showNewProject: boolean;
  onToggleNewProject: () => void;
  newProjectName: string;
  onNameChange: (value: string) => void;
  onCreate: () => void;
  createError: string | null;
  projectMenu: string | null;
  onToggleMenu: (id: string) => void;
  onSelectProject: (id: string) => void;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onDelete: (id: string, name: string) => void;
}) {
  if (collapsed) return null;
  return (
    <div className="p-2 border-t border-slate-200 dark:border-slate-800 mt-1 shrink-0" tabIndex={0} role="region" aria-label="Projects list">
      <div className="flex items-center justify-between px-3 py-2">
        <span className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">Projects</span>
        <button onClick={onToggleNewProject} className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500" aria-label="Create new project">
          <Plus size={14} />
        </button>
      </div>
      {showNewProject && <NewProjectForm value={newProjectName} onChange={onNameChange} onSubmit={onCreate} error={createError} />}
      <div className="space-y-0.5" role="group" aria-label="Projects">
        {projects.map((project) => (
          <ProjectRow
            key={project.id}
            project={project}
            activeProjectId={activeProjectId}
            menuOpen={projectMenu === project.id}
            onSelect={() => onSelectProject(project.id)}
            onToggleMenu={() => onToggleMenu(project.id)}
            onPause={() => onPause(project.id)}
            onResume={() => onResume(project.id)}
            onDelete={() => onDelete(project.id, project.name)}
          />
        ))}
      </div>
      {projects.length === 0 && <p className="px-3 py-4 text-sm text-slate-400 text-center">No projects yet. Create one to get started.</p>}
    </div>
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
  const { user } = useAuthStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Auto-expand secondary nav when the active view is a secondary item
  useEffect(() => {
    if (SECONDARY_NAV_IDS.has(activeView as ViewId)) {
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

  return (
    <aside
      role="navigation"
      aria-label="Main navigation"
      className={cn(
        "shrink-0 flex flex-col border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      <SidebarHeader collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} onViewChange={onViewChange} />

      {/* Scrollable content area — nav + projects share a single scroll container
           so opening "More" doesn't push projects off-screen */}
      <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
      <SearchControl collapsed={collapsed} onSearchOpen={onSearchOpen} />
      <ViewNavigation
        activeView={activeView}
        onViewChange={onViewChange}
        collapsed={collapsed}
        showSecondary={showSecondary}
        onToggleSecondary={() => setShowSecondary(!showSecondary)}
        role={user?.role}
      />

      <ProjectsSection
        collapsed={collapsed}
        projects={projects}
        activeProjectId={activeProjectId}
        showNewProject={showNewProject}
        onToggleNewProject={() => setShowNewProject(!showNewProject)}
        newProjectName={newProjectName}
        onNameChange={(value) => { setNewProjectName(value); setCreateError(null); }}
        onCreate={handleCreateProject}
        createError={createError}
        projectMenu={projectMenu}
        onToggleMenu={(id) => setProjectMenu(projectMenu === id ? null : id)}
        onSelectProject={setActiveProject}
        onPause={(id) => { pauseProject(id); setProjectMenu(null); }}
        onResume={(id) => { resumeProject(id); setProjectMenu(null); }}
        onDelete={(id, name) => { if (window.confirm(`Delete "${name}"?`)) deleteProject(id); setProjectMenu(null); }}
      />

      </div>{/* end scrollable content area */}

      {/* User Menu */}
      <UserMenu collapsed={collapsed} />
    </aside>
  );
}
