"use client";

/**
 * ProjectSettingsView — combines project management + research metrics.
 *
 * Sections:
 * 1. Project header: name (editable), phase selector, pause/resume
 * 2. Research metrics (from old MetricsView)
 * 3. Team access (per-project member management, team mode only)
 * 4. Linked folder management
 * 5. Danger zone: export + delete
 */

import { useEffect, useState, useCallback } from "react";
import {
  Settings2, BarChart3, Target, CheckCircle, AlertCircle, Loader2,
  Users, UserPlus, MoreVertical, Trash2, Pause, Play, FolderOpen,
  Download, AlertTriangle, X, Pencil, Check,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { useAuthStore } from "@/stores/authStore";
import { projects as projectsApi, users as usersApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import ViewOnboarding from "@/components/common/ViewOnboarding";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ──

interface ProjectMetrics {
  findings: { nuggets: number; facts: number; insights: number; recommendations: number; total: number };
  tasks: { total: number; done: number; in_progress: number; completion_rate: number };
  quality: { avg_confidence: number; messages: number };
  by_phase: Record<string, { nuggets: number; facts: number; insights: number; recommendations: number; total: number }>;
}

interface MemberInfo {
  id: string;
  user_id: string;
  role: string;
  username: string;
  email: string;
  display_name: string;
  last_active: string | null;
  added_at: string | null;
}

// ── Helpers ──

function _authHeaders(): Record<string, string> {
  const t = localStorage.getItem("istara_token");
  return t ? { Authorization: `Bearer ${t}` } : {};
}

function timeAgo(iso: string | null): string {
  if (!iso) return "Never";
  const diff = (Date.now() - new Date(iso).getTime()) / 60000;
  if (diff < 1) return "Just now";
  if (diff < 60) return `${Math.round(diff)}m ago`;
  if (diff < 1440) return `${Math.round(diff / 60)}h ago`;
  return `${Math.round(diff / 1440)}d ago`;
}

// ── Main Component ──

export default function ProjectSettingsView() {
  const { activeProjectId, activeProject, updateProject, pauseProject, resumeProject, deleteProject } = useProjectStore();
  const { user, teamMode } = useAuthStore();
  const project = activeProject();
  const isAdmin = user?.role === "admin";

  // Metrics
  const [metrics, setMetrics] = useState<ProjectMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(true);

  // Members
  const [members, setMembers] = useState<MemberInfo[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [showAddMember, setShowAddMember] = useState(false);
  const [serverUsers, setServerUsers] = useState<any[]>([]);
  const [memberMenu, setMemberMenu] = useState<string | null>(null);

  // Edit name
  const [editingName, setEditingName] = useState(false);
  const [editName, setEditName] = useState("");

  // Delete confirmation
  const [showDelete, setShowDelete] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");

  // Fetch metrics
  useEffect(() => {
    if (!activeProjectId) return;
    setMetricsLoading(true);
    fetch(`${API_BASE}/api/metrics/${activeProjectId}`, { headers: _authHeaders() })
      .then((r) => r.ok ? r.json() : null)
      .then(setMetrics)
      .catch(() => setMetrics(null))
      .finally(() => setMetricsLoading(false));
  }, [activeProjectId]);

  // Fetch members
  const fetchMembers = useCallback(async () => {
    if (!activeProjectId || !teamMode) return;
    setMembersLoading(true);
    try {
      const data = await fetch(`${API_BASE}/api/projects/${activeProjectId}/members`, { headers: _authHeaders() }).then((r) => r.json());
      setMembers(data.members || []);
    } catch {
      setMembers([]);
    }
    setMembersLoading(false);
  }, [activeProjectId, teamMode]);

  useEffect(() => { fetchMembers(); }, [fetchMembers]);

  // Handlers
  const handleSaveName = async () => {
    if (!editName.trim() || !activeProjectId) return;
    await updateProject(activeProjectId, { name: editName.trim() });
    setEditingName(false);
  };

  const handleTogglePause = async () => {
    if (!activeProjectId || !project) return;
    if (project.is_paused) {
      await resumeProject(activeProjectId);
    } else {
      await pauseProject(activeProjectId);
    }
  };

  const handleDelete = async () => {
    if (!activeProjectId || !project) return;
    if (deleteConfirm !== project.name) return;
    await deleteProject(activeProjectId);
    setShowDelete(false);
    setDeleteConfirm("");
  };

  const handleAddMember = async (userId: string) => {
    if (!activeProjectId) return;
    try {
      await fetch(`${API_BASE}/api/projects/${activeProjectId}/members`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ..._authHeaders() },
        body: JSON.stringify({ user_id: userId, role: "member" }),
      });
      setShowAddMember(false);
      fetchMembers();
    } catch {}
  };

  const handleRemoveMember = async (userId: string) => {
    if (!activeProjectId) return;
    await fetch(`${API_BASE}/api/projects/${activeProjectId}/members/${userId}`, {
      method: "DELETE",
      headers: _authHeaders(),
    });
    setMemberMenu(null);
    fetchMembers();
  };

  const handleChangeRole = async (userId: string, newRole: string) => {
    if (!activeProjectId) return;
    await fetch(`${API_BASE}/api/projects/${activeProjectId}/members/${userId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ..._authHeaders() },
      body: JSON.stringify({ role: newRole }),
    });
    setMemberMenu(null);
    fetchMembers();
  };

  const openAddMember = async () => {
    setShowAddMember(true);
    try {
      const data = await usersApi.list();
      setServerUsers(data.filter((u: any) => !members.find((m) => m.user_id === u.id)));
    } catch {
      setServerUsers([]);
    }
  };

  if (!activeProjectId || !project) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <p>Select a project to view settings.</p>
      </div>
    );
  }

  const maxPhaseTotal = metrics ? Math.max(...Object.values(metrics.by_phase).map((p) => p.total), 1) : 1;

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <ViewOnboarding viewId="project-settings" title="Project Settings" description="Manage your project, track research metrics, and control team access." chatPrompt="What can I configure in project settings?" />
      <div className="max-w-4xl mx-auto space-y-6">

        {/* ── Project Header ── */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Settings2 size={20} className="text-istara-600" />
              {editingName ? (
                <div className="flex items-center gap-2">
                  <input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSaveName()}
                    className="text-lg font-semibold bg-transparent border-b-2 border-istara-500 focus:outline-none text-slate-900 dark:text-white"
                    autoFocus
                  />
                  <button onClick={handleSaveName} className="p-1 text-green-600 hover:bg-green-50 rounded"><Check size={16} /></button>
                  <button onClick={() => setEditingName(false)} className="p-1 text-slate-400 hover:bg-slate-100 rounded"><X size={16} /></button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{project.name}</h2>
                  {isAdmin && (
                    <button onClick={() => { setEditName(project.name); setEditingName(true); }} className="p-1 text-slate-400 hover:text-slate-600 rounded" aria-label="Edit project name">
                      <Pencil size={14} />
                    </button>
                  )}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              {isAdmin && (
                <button
                  onClick={handleTogglePause}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                    project.is_paused
                      ? "bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400"
                      : "bg-yellow-50 text-yellow-700 hover:bg-yellow-100 dark:bg-yellow-900/20 dark:text-yellow-400"
                  )}
                >
                  {project.is_paused ? <><Play size={14} /> Resume</> : <><Pause size={14} /> Pause</>}
                </button>
              )}
              <span className={cn(
                "px-2 py-1 rounded text-xs font-medium capitalize",
                project.is_paused ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" : "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
              )}>
                {project.is_paused ? "Paused" : project.phase}
              </span>
            </div>
          </div>
          {project.description && (
            <p className="text-sm text-slate-500 mt-2 ml-8">{project.description}</p>
          )}
        </div>

        {/* ── Research Metrics ── */}
        {metricsLoading ? (
          <div className="flex items-center justify-center py-12 text-slate-400">
            <Loader2 size={20} className="animate-spin mr-2" /> Loading metrics...
          </div>
        ) : metrics ? (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard emoji="📊" label="Total Findings" value={metrics.findings.total} color="border-istara-500" />
              <MetricCard emoji="✅" label="Task Completion" value={`${metrics.tasks.completion_rate}%`}
                sub={`${metrics.tasks.done}/${metrics.tasks.total} tasks`}
                color={metrics.tasks.completion_rate >= 75 ? "border-green-500" : metrics.tasks.completion_rate >= 50 ? "border-yellow-500" : "border-red-500"} />
              <MetricCard emoji="🎯" label="Avg Confidence" value={`${Math.round(metrics.quality.avg_confidence * 100)}%`}
                color={metrics.quality.avg_confidence >= 0.7 ? "border-green-500" : "border-yellow-500"} />
              <MetricCard emoji="💬" label="Messages" value={metrics.quality.messages} color="border-blue-500" />
            </div>

            {/* Atomic Research Breakdown */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
              <h3 className="font-medium text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <Target size={16} /> Atomic Research Breakdown
              </h3>
              <div className="grid grid-cols-4 gap-4 text-center">
                {[
                  { emoji: "✨", label: "Nuggets", value: metrics.findings.nuggets, color: "text-purple-600" },
                  { emoji: "📄", label: "Facts", value: metrics.findings.facts, color: "text-blue-600" },
                  { emoji: "💡", label: "Insights", value: metrics.findings.insights, color: "text-yellow-600" },
                  { emoji: "🎯", label: "Recs", value: metrics.findings.recommendations, color: "text-green-600" },
                ].map((item) => (
                  <div key={item.label} className="bg-slate-50 dark:bg-slate-900 rounded-lg p-4">
                    <span className="text-2xl">{item.emoji}</span>
                    <p className={cn("text-3xl font-bold mt-1", item.color)}>{item.value}</p>
                    <p className="text-xs text-slate-500 mt-1">{item.label}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Double Diamond Coverage */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
              <h3 className="font-medium text-slate-900 dark:text-white mb-4">💎 Double Diamond Coverage</h3>
              <div className="space-y-4">
                {Object.entries(metrics.by_phase).map(([phase, data]) => (
                  <div key={phase}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-slate-700 dark:text-slate-300 capitalize font-medium">💎 {phase}</span>
                      <span className="text-xs text-slate-500">{data.total} findings</span>
                    </div>
                    <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-3">
                      <div className="bg-istara-500 h-3 rounded-full transition-all duration-500" style={{ width: `${(data.total / maxPhaseTotal) * 100}%` }} />
                    </div>
                    <div className="flex gap-4 mt-1 text-[10px] text-slate-400">
                      <span>✨ {data.nuggets}</span><span>📄 {data.facts}</span><span>💡 {data.insights}</span><span>🎯 {data.recommendations}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Task Progress */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
              <h3 className="font-medium text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <CheckCircle size={16} /> Task Progress
              </h3>
              <div className="flex items-center gap-6">
                <div className="relative w-24 h-24">
                  <svg className="w-24 h-24 -rotate-90" viewBox="0 0 36 36">
                    <path className="text-slate-200 dark:text-slate-700" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" />
                    <path className="text-istara-500" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" strokeDasharray={`${metrics.tasks.completion_rate}, 100`} />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-lg font-bold text-slate-900 dark:text-white">{Math.round(metrics.tasks.completion_rate)}%</span>
                  </div>
                </div>
                <div className="space-y-2 text-sm">
                  <p className="text-slate-600 dark:text-slate-400"><span className="font-semibold text-slate-900 dark:text-white">{metrics.tasks.done}</span> completed</p>
                  <p className="text-slate-600 dark:text-slate-400"><span className="font-semibold text-blue-600">{metrics.tasks.in_progress}</span> in progress</p>
                  <p className="text-slate-600 dark:text-slate-400"><span className="font-semibold text-slate-500">{metrics.tasks.total - metrics.tasks.done - metrics.tasks.in_progress}</span> remaining</p>
                </div>
              </div>
            </div>
          </>
        ) : null}

        {/* ── Team Access (team mode only) ── */}
        {teamMode && (
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
                <Users size={16} /> Team Access
              </h3>
              {isAdmin && (
                <button onClick={openAddMember} className="flex items-center gap-1 px-2.5 py-1 text-xs bg-istara-600 text-white rounded-lg hover:bg-istara-700">
                  <UserPlus size={12} /> Add Member
                </button>
              )}
            </div>

            {/* Add member modal */}
            {showAddMember && (
              <div className="mb-4 p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Add server user to this project</span>
                  <button onClick={() => setShowAddMember(false)} className="text-slate-400 hover:text-slate-600"><X size={14} /></button>
                </div>
                {serverUsers.length === 0 ? (
                  <p className="text-xs text-slate-400 py-2">All server users are already members.</p>
                ) : (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {serverUsers.map((u) => (
                      <button key={u.id} onClick={() => handleAddMember(u.id)} className="w-full text-left px-2.5 py-1.5 rounded text-sm hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-between">
                        <span className="text-slate-700 dark:text-slate-300">{u.display_name || u.username}</span>
                        <span className="text-xs text-slate-400">{u.role}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Member list */}
            {membersLoading ? (
              <div className="flex items-center gap-2 text-sm text-slate-400 py-4">
                <Loader2 size={14} className="animate-spin" /> Loading members...
              </div>
            ) : members.length === 0 ? (
              <p className="text-sm text-slate-400 py-2">No members added yet. The project creator has full access.</p>
            ) : (
              <div className="space-y-1">
                {members.map((m) => (
                  <div key={m.id} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900 group">
                    <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-600 dark:text-slate-400">
                      {(m.display_name || m.username || "?").charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-800 dark:text-slate-200">{m.display_name || m.username}</div>
                      <div className="text-xs text-slate-400">{m.email}</div>
                    </div>
                    <span className={cn(
                      "px-2 py-0.5 rounded text-[10px] font-medium capitalize",
                      m.role === "admin" ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
                        : m.role === "viewer" ? "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
                          : "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                    )}>
                      {m.role}
                    </span>
                    <span className="text-[10px] text-slate-400 w-16 text-right">{timeAgo(m.last_active)}</span>
                    {isAdmin && (
                      <div className="relative">
                        <button onClick={() => setMemberMenu(memberMenu === m.user_id ? null : m.user_id)} className="p-1 rounded text-slate-400 hover:text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity">
                          <MoreVertical size={14} />
                        </button>
                        {memberMenu === m.user_id && (
                          <div className="absolute right-0 top-8 w-44 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg z-10 py-1">
                            {["admin", "member", "viewer"].filter((r) => r !== m.role).map((r) => (
                              <button key={r} onClick={() => handleChangeRole(m.user_id, r)} className="w-full text-left px-3 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 capitalize">
                                Set as {r}
                              </button>
                            ))}
                            <hr className="my-1 border-slate-200 dark:border-slate-700" />
                            <button onClick={() => handleRemoveMember(m.user_id)} className="w-full text-left px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20">
                              Remove from project
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Linked Folder ── */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2 mb-3">
            <FolderOpen size={16} /> Linked Folder
          </h3>
          {project.watch_folder_path ? (
            <div className="flex items-center justify-between">
              <code className="text-sm text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-900 px-2 py-1 rounded">{project.watch_folder_path}</code>
              {isAdmin && (
                <button
                  onClick={() => updateProject(activeProjectId!, { watch_folder_path: null })}
                  className="text-xs text-red-500 hover:text-red-600"
                >
                  Unlink
                </button>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-400">No folder linked. Link a folder in the onboarding tour or via the API.</p>
          )}
        </div>

        {/* ── Danger Zone ── */}
        {isAdmin && (
          <div className="bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-200 dark:border-red-800 p-5">
            <h3 className="font-medium text-red-800 dark:text-red-300 flex items-center gap-2 mb-3">
              <AlertTriangle size={16} /> Danger Zone
            </h3>
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  fetch(`${API_BASE}/api/projects/${activeProjectId}/export`, { method: "POST", headers: _authHeaders() })
                    .then(() => window.dispatchEvent(new CustomEvent("istara:toast", { detail: { type: "success", title: "Exported", message: "Project exported to data/exports/" } })))
                    .catch(() => window.dispatchEvent(new CustomEvent("istara:toast", { detail: { type: "warning", title: "Export Failed", message: "Could not export project." } })));
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <Download size={14} /> Export
              </button>
              <button
                onClick={() => setShowDelete(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                <Trash2 size={14} /> Delete Project
              </button>
            </div>

            {showDelete && (
              <div className="mt-4 p-3 bg-white dark:bg-slate-800 rounded-lg border border-red-300 dark:border-red-700">
                <p className="text-sm text-red-700 dark:text-red-400 mb-2">
                  Type <strong>{project.name}</strong> to confirm deletion. This cannot be undone.
                </p>
                <div className="flex gap-2">
                  <input
                    value={deleteConfirm}
                    onChange={(e) => setDeleteConfirm(e.target.value)}
                    placeholder={project.name}
                    className="flex-1 px-2.5 py-1.5 text-sm rounded border border-red-300 dark:border-red-700 bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                  <button
                    onClick={handleDelete}
                    disabled={deleteConfirm !== project.name}
                    className="px-3 py-1.5 text-sm bg-red-600 text-white rounded disabled:opacity-40 disabled:cursor-not-allowed hover:bg-red-700"
                  >
                    Delete
                  </button>
                  <button onClick={() => { setShowDelete(false); setDeleteConfirm(""); }} className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded">
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}

// ── Sub-components ──

function MetricCard({ emoji, label, value, sub, color }: { emoji: string; label: string; value: number | string; sub?: string; color: string }) {
  return (
    <div className={cn("rounded-xl border-l-4 bg-white dark:bg-slate-800 p-4", color)}>
      <span className="text-xl">{emoji}</span>
      <p className="text-3xl font-bold text-slate-900 dark:text-white mt-1">{value}</p>
      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
      {sub && <p className="text-[10px] text-slate-400">{sub}</p>}
    </div>
  );
}
