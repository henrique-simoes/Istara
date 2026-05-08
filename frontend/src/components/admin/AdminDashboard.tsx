"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, Check, Copy, Cpu, FolderOpen, KeyRound, Lock, RefreshCw, Shield, Trash2, UserCog, Users, XCircle } from "lucide-react";

import { admin as adminApi, permissionRequests } from "@/lib/api";
import type { PermissionRequestItem } from "@/lib/types";
import { useAuthStore } from "@/stores/authStore";
import ViewOnboarding from "@/components/common/ViewOnboarding";

function MetricCard({ label, value, icon: Icon, note }: { label: string; value: string | number; icon: any; note?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950 dark:text-white">{value}</p>
        </div>
        <Icon size={22} className="text-istara-600 dark:text-istara-400" />
      </div>
      {note && <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">{note}</p>}
    </div>
  );
}

export default function AdminDashboard() {
  const { user } = useAuthStore();
  const [overview, setOverview] = useState<any>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [memberships, setMemberships] = useState<any[]>([]);
  const [connections, setConnections] = useState<{ user_invites: any[]; compute_donations: any[] } | null>(null);
  const [requests, setRequests] = useState<PermissionRequestItem[]>([]);
  const [inviteRole, setInviteRole] = useState("researcher");
  const [inviteLabel, setInviteLabel] = useState("");
  const [generatedString, setGeneratedString] = useState("");
  const [accessProjectId, setAccessProjectId] = useState("");
  const [accessUserId, setAccessUserId] = useState("");
  const [accessRole, setAccessRole] = useState<"project_admin" | "researcher" | "viewer">("researcher");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canAdmin = user?.role === "admin";

  const load = useCallback(async () => {
    if (!canAdmin) return;
    setLoading(true);
    setError("");
    try {
      const [overviewData, projectData, userData, accessData, connectionData, requestData] = await Promise.all([
        adminApi.overview(),
        adminApi.projects(),
        adminApi.users(),
        adminApi.access(),
        adminApi.connectionStrings(),
        permissionRequests.list({ status: "pending" }),
      ]);
      setOverview(overviewData);
      setProjects(projectData.projects || []);
      setUsers(userData.users || []);
      setMemberships(accessData.memberships || []);
      setConnections(connectionData);
      setRequests(requestData.requests || []);
    } catch (err: any) {
      setError(err.message || "Could not load admin dashboard.");
    } finally {
      setLoading(false);
    }
  }, [canAdmin]);

  useEffect(() => {
    load();
  }, [load]);

  const taskSummary = useMemo(() => {
    const byStatus = overview?.tasks?.by_status || {};
    return `${byStatus.backlog || 0} backlog / ${byStatus.in_progress || 0} active / ${byStatus.in_review || 0} review`;
  }, [overview]);

  const serverUrl = useMemo(() => {
    if (typeof window === "undefined") return "";
    return window.location.origin;
  }, []);

  const generateInvite = async () => {
    setError("");
    const result = await adminApi.generateUserInvite({
      server_url: serverUrl,
      label: inviteLabel || inviteRole,
      role: inviteRole,
    });
    setGeneratedString(result.connection_string || "");
    await load();
  };

  const generateDonation = async () => {
    setError("");
    const result = await adminApi.generateComputeDonation({
      server_url: serverUrl,
      label: inviteLabel || "Compute donation",
    });
    setGeneratedString(result.connection_string || "");
    await load();
  };

  const updateGlobalRole = async (userId: string, role: "admin" | "researcher" | "viewer") => {
    await adminApi.updateUserRole(userId, role);
    await load();
  };

  const addAccess = async () => {
    if (!accessProjectId || !accessUserId) return;
    await adminApi.addProjectMember(accessProjectId, accessUserId, accessRole);
    await load();
  };

  const reviewRequest = async (id: string, status: "approved" | "rejected") => {
    await permissionRequests.review(id, { status });
    await load();
  };

  const deleteProject = async (projectId: string) => {
    if (!confirm("Delete this project and all associated data? This cannot be undone.")) return;
    await adminApi.deleteProject(projectId);
    await load();
  };

  if (!canAdmin) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="max-w-md text-center">
          <Shield className="mx-auto mb-4 text-slate-400" size={36} />
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Admin Access Required</h2>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Only global admins can view system-wide projects, access, compute, and invite metrics.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-slate-50 p-6 dark:bg-slate-950">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-950 dark:text-white">Admin Dashboard</h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">System-wide project, access, compute, and usage controls.</p>
          </div>
          <button onClick={load} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm hover:bg-slate-100 disabled:opacity-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800">
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>

        <ViewOnboarding viewId="admin" title="Admin Console" description="Manage users, project access, permission requests, invite strings, compute donation strings, and system-wide release controls." chatPrompt="What can global admins manage here?" />

        {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">{error}</div>}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Users" value={overview?.users?.total ?? "—"} icon={Users} note={`${overview?.users?.admins ?? 0} admins, ${overview?.users?.viewers ?? 0} viewers`} />
          <MetricCard label="Projects" value={overview?.projects?.total ?? "—"} icon={FolderOpen} note={`${overview?.projects?.memberships ?? 0} memberships`} />
          <MetricCard label="Compute" value={overview?.compute?.healthy_llm_servers ?? "—"} icon={Cpu} note={`${overview?.compute?.llm_servers ?? 0} LLM servers, ${overview?.compute?.relay_nodes ?? 0} relay nodes`} />
          <MetricCard label="Tasks" value={overview?.tasks?.total ?? "—"} icon={Activity} note={taskSummary} />
        </div>

        <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Shield size={16} /> Permission Requests</h2>
          {requests.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">No pending project admin requests.</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {requests.slice(0, 12).map((item) => {
                const project = projects.find((candidate) => candidate.id === item.project_id);
                return (
                  <div key={item.id} className="rounded-md border border-slate-100 p-3 text-sm dark:border-slate-800">
                    <div className="font-medium text-slate-900 dark:text-white">{item.title || item.action}</div>
                    <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      {project?.name || item.project_id} · {item.requester_username || item.requester_user_id}
                    </div>
                    {item.details && <p className="mt-2 line-clamp-2 text-xs text-slate-600 dark:text-slate-300">{item.details}</p>}
                    <div className="mt-3 flex gap-2">
                      <button onClick={() => reviewRequest(item.id, "approved")} className="inline-flex items-center gap-1 rounded-md bg-green-600 px-2 py-1 text-xs font-medium text-white hover:bg-green-700">
                        <Check size={12} /> Approve
                      </button>
                      <button onClick={() => reviewRequest(item.id, "rejected")} className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
                        <XCircle size={12} /> Reject
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <div className="grid gap-4 xl:grid-cols-3">
          <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 xl:col-span-2">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><FolderOpen size={16} /> All Projects</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-slate-500 dark:text-slate-400">
                  <tr><th className="py-2">Project</th><th>Members</th><th>Tasks</th><th>Documents</th><th>Findings</th><th></th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {projects.slice(0, 12).map((project) => (
                    <tr key={project.id} className="text-slate-700 dark:text-slate-200">
                      <td className="py-2 font-medium">{project.name}</td>
                      <td>{project.member_count}</td>
                      <td>{project.task_count}</td>
                      <td>{project.document_count}</td>
                      <td>{project.finding_count}</td>
                      <td className="text-right">
                        <button onClick={() => deleteProject(project.id)} className="rounded p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40" title="Delete project">
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><KeyRound size={16} /> Connection Strings</h2>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between"><span>User invites</span><strong>{connections?.user_invites?.length ?? 0}</strong></div>
              <div className="flex items-center justify-between"><span>Compute donations</span><strong>{connections?.compute_donations?.length ?? 0}</strong></div>
              <input value={inviteLabel} onChange={(event) => setInviteLabel(event.target.value)} placeholder="Label" className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-950" />
              <select value={inviteRole} onChange={(event) => setInviteRole(event.target.value)} className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-950">
                <option value="researcher">Researcher invite</option>
                <option value="viewer">Viewer invite</option>
                <option value="admin">Admin invite</option>
              </select>
              <div className="grid grid-cols-2 gap-2">
                <button onClick={generateInvite} className="rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-700 dark:bg-white dark:text-slate-950">Generate Invite</button>
                <button onClick={generateDonation} className="rounded-md border border-slate-200 px-3 py-2 text-xs font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">Donation String</button>
              </div>
              {generatedString && (
                <button onClick={() => navigator.clipboard?.writeText(generatedString)} className="flex w-full items-center gap-2 rounded-md bg-slate-100 p-2 text-left text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  <Copy size={14} />
                  <span className="truncate">{generatedString}</span>
                </button>
              )}
              <p className="rounded-md bg-slate-100 p-3 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                Invite strings and compute donation strings are separate token types. Token usage metrics are marked as not collected until durable token accounting lands.
              </p>
            </div>
          </section>
        </div>

        <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><Lock size={16} /> Users</h2>
          <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {users.slice(0, 18).map((item) => (
              <div key={item.id} className="rounded-md border border-slate-100 p-3 text-sm dark:border-slate-800">
                <div className="font-medium text-slate-900 dark:text-white">{item.display_name || item.username}</div>
                <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{item.project_count} projects</div>
                <select value={item.role} onChange={(event) => updateGlobalRole(item.id, event.target.value as any)} className="mt-2 w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-950">
                  <option value="admin">Admin</option>
                  <option value="researcher">Researcher</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white"><UserCog size={16} /> Project Access</h2>
          <div className="grid gap-2 md:grid-cols-4">
            <select value={accessProjectId} onChange={(event) => setAccessProjectId(event.target.value)} className="rounded-md border border-slate-200 bg-white px-2 py-2 text-sm dark:border-slate-700 dark:bg-slate-950">
              <option value="">Project</option>
              {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
            </select>
            <select value={accessUserId} onChange={(event) => setAccessUserId(event.target.value)} className="rounded-md border border-slate-200 bg-white px-2 py-2 text-sm dark:border-slate-700 dark:bg-slate-950">
              <option value="">User</option>
              {users.map((item) => <option key={item.id} value={item.id}>{item.display_name || item.username}</option>)}
            </select>
            <select value={accessRole} onChange={(event) => setAccessRole(event.target.value as any)} className="rounded-md border border-slate-200 bg-white px-2 py-2 text-sm dark:border-slate-700 dark:bg-slate-950">
              <option value="project_admin">Project admin</option>
              <option value="researcher">Researcher</option>
              <option value="viewer">Viewer</option>
            </select>
            <button onClick={addAccess} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700 dark:bg-white dark:text-slate-950">Grant Access</button>
          </div>
          <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {memberships.slice(0, 18).map((member) => (
              <div key={member.id} className="rounded-md border border-slate-100 p-3 text-sm dark:border-slate-800">
                <div className="font-medium text-slate-900 dark:text-white">{member.project_name || member.project_id}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">{member.username || member.user_id}</div>
                <select value={member.role} onChange={(event) => adminApi.updateProjectMember(member.project_id, member.user_id, event.target.value as any).then(load)} className="mt-2 w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-950">
                  <option value="project_admin">Project admin</option>
                  <option value="researcher">Researcher</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
