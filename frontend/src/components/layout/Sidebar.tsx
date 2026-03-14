"use client";

import { useEffect, useState } from "react";
import {
  FolderOpen,
  Plus,
  Diamond,
  Bot,
  LayoutDashboard,
  FileText,
  ChevronLeft,
  ChevronRight,
  Settings,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { cn, phaseLabel } from "@/lib/utils";

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
}

export default function Sidebar({ activeView, onViewChange }: SidebarProps) {
  const {
    projects,
    activeProjectId,
    fetchProjects,
    setActiveProject,
    createProject,
  } = useProjectStore();
  const [collapsed, setCollapsed] = useState(false);
  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;
    await createProject(newProjectName.trim());
    setNewProjectName("");
    setShowNewProject(false);
  };

  const navItems = [
    { id: "chat", icon: Bot, label: "Chat" },
    { id: "findings", icon: Diamond, label: "Findings" },
    { id: "tasks", icon: LayoutDashboard, label: "Tasks" },
    { id: "context", icon: FileText, label: "Context" },
    { id: "settings", icon: Settings, label: "Settings" },
  ];

  return (
    <aside
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
            <span className="font-bold text-lg text-slate-900 dark:text-white">ReClaw</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500"
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="p-2 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onViewChange(item.id)}
            className={cn(
              "flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition-colors",
              activeView === item.id
                ? "bg-reclaw-100 text-reclaw-700 dark:bg-reclaw-900/30 dark:text-reclaw-400"
                : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            )}
          >
            <item.icon size={18} />
            {!collapsed && <span>{item.label}</span>}
          </button>
        ))}
      </nav>

      {/* Projects */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-2">
          <div className="flex items-center justify-between px-3 py-2">
            <span className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
              Projects
            </span>
            <button
              onClick={() => setShowNewProject(!showNewProject)}
              className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500"
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
                onChange={(e) => setNewProjectName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateProject()}
                className="w-full px-2 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                autoFocus
              />
            </div>
          )}

          <div className="space-y-0.5">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => setActiveProject(project.id)}
                className={cn(
                  "flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm transition-colors",
                  activeProjectId === project.id
                    ? "bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white"
                    : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                )}
              >
                <FolderOpen size={14} className="shrink-0" />
                <div className="text-left truncate">
                  <div className="truncate">{project.name}</div>
                  <div className="text-xs text-slate-400">{phaseLabel(project.phase)}</div>
                </div>
              </button>
            ))}
          </div>

          {projects.length === 0 && (
            <p className="px-3 py-4 text-sm text-slate-400 text-center">
              No projects yet.
              <br />
              Create one to get started.
            </p>
          )}
        </div>
      )}
    </aside>
  );
}
