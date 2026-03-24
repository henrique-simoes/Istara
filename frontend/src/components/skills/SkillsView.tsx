"use client";

import { useEffect, useState } from "react";
import {
  Wand2,
  Plus,
  ChevronDown,
  ChevronRight,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  ToggleLeft,
  ToggleRight,
  Sparkles,
  AlertCircle,
  RefreshCw,
  Edit3,
  Trash2,
  Play,
  Eye,
  Upload,
  Search,
} from "lucide-react";
import { skills as skillsApi } from "@/lib/api";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";

type PhaseFilter = "all" | "discover" | "define" | "develop" | "deliver";
type Tab = "catalog" | "proposals" | "create";

interface SkillData {
  name: string;
  display_name: string;
  description: string;
  phase: string;
  skill_type: string;
  version: string;
  enabled: boolean;
  plan_prompt?: string;
  execute_prompt?: string;
  output_schema?: string;
  changelog?: { version: string; date: string; changes: string }[];
  health?: {
    health_score: number;
    executions: number;
    success_rate: number;
    avg_quality: number;
    completeness: number;
    last_used: string | null;
    pending_proposals: number;
  };
  usage?: {
    executions: number;
    successes: number;
    failures: number;
    avg_quality: number;
    success_rate: number;
    last_used: string | null;
  };
}

interface ProposalData {
  id: string;
  skill_name: string;
  field: string;
  current_value: string;
  proposed_value: string;
  reason: string;
  confidence: number;
  status: string;
  created_at: string;
  reviewed_at: string | null;
}

const PHASE_COLORS: Record<string, string> = {
  discover: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  define: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  develop: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  deliver: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
};

function HealthBadge({ score }: { score: number }) {
  const color =
    score >= 0.7
      ? "text-green-600"
      : score >= 0.4
        ? "text-amber-500"
        : "text-red-500";
  return (
    <span className={cn("text-xs font-mono font-medium", color)}>
      {(score * 100).toFixed(0)}%
    </span>
  );
}

export default function SkillsView() {
  const [tab, setTab] = useState<Tab>("catalog");
  const [allSkills, setAllSkills] = useState<SkillData[]>([]);
  const [healthMap, setHealthMap] = useState<Record<string, any>>({});
  const [phaseFilter, setPhaseFilter] = useState<PhaseFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null);
  const [editingSkill, setEditingSkill] = useState<string | null>(null);
  const [proposals, setProposals] = useState<ProposalData[]>([]);
  const [phaseCounts, setPhaseCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  // Create form
  const [newSkill, setNewSkill] = useState({
    name: "",
    display_name: "",
    description: "",
    phase: "discover",
    skill_type: "analysis",
    plan_prompt: "",
    execute_prompt: "",
    output_schema: "",
  });

  const { activeProjectId } = useProjectStore();

  const fetchSkills = async () => {
    setLoading(true);
    try {
      const [skillsRes, healthRes] = await Promise.all([
        skillsApi.list(),
        skillsApi.health(),
      ]);
      setAllSkills(skillsRes.skills || []);
      setPhaseCounts(skillsRes.by_phase || {});
      const hMap: Record<string, any> = {};
      for (const h of healthRes.skills || []) {
        hMap[h.name] = h;
      }
      setHealthMap(hMap);
    } catch (e) {
      console.error("Failed to load skills:", e);
    }
    setLoading(false);
  };

  const fetchProposals = async () => {
    try {
      const res = await skillsApi.proposals.all();
      setProposals(res.proposals || []);
    } catch (e) {
      console.error("Failed to load proposals:", e);
    }
  };

  useEffect(() => {
    fetchSkills();
    fetchProposals();
  }, []);

  const filtered = allSkills.filter((s) => {
    if (phaseFilter !== "all" && s.phase !== phaseFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        s.name.includes(q) ||
        s.display_name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const pendingProposals = proposals.filter((p) => p.status === "pending");

  const handleToggle = async (name: string, enabled: boolean) => {
    try {
      await skillsApi.toggle(name, !enabled);
      await fetchSkills();
    } catch (e) {
      console.error("Toggle failed:", e);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await skillsApi.proposals.approve(id);
      await Promise.all([fetchSkills(), fetchProposals()]);
    } catch (e) {
      console.error("Approve failed:", e);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await skillsApi.proposals.reject(id);
      await fetchProposals();
    } catch (e) {
      console.error("Reject failed:", e);
    }
  };

  const handleCreate = async () => {
    if (!newSkill.name || !newSkill.display_name) return;
    try {
      await skillsApi.create(newSkill);
      setNewSkill({
        name: "",
        display_name: "",
        description: "",
        phase: "discover",
        skill_type: "analysis",
        plan_prompt: "",
        execute_prompt: "",
        output_schema: "",
      });
      setTab("catalog");
      await fetchSkills();
    } catch (e) {
      console.error("Create failed:", e);
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete skill "${name}"? It will be backed up.`)) return;
    try {
      await skillsApi.delete(name);
      setExpandedSkill(null);
      await fetchSkills();
    } catch (e) {
      console.error("Delete failed:", e);
    }
  };

  const handleExecute = async (name: string) => {
    if (!activeProjectId) {
      alert("Select a project first.");
      return;
    }
    try {
      await skillsApi.execute(name, { project_id: activeProjectId });
      await fetchSkills();
    } catch (e) {
      console.error("Execute failed:", e);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <RefreshCw size={20} className="animate-spin mr-2" />
        Loading skills...
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto space-y-5" tabIndex={0} role="region" aria-label="Skills catalog">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wand2 size={20} className="text-reclaw-600" />
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            Skills
          </h2>
          <span className="text-sm text-slate-400">
            {allSkills.length} total
          </span>
        </div>
        <button
          onClick={fetchSkills}
          className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400"
          aria-label="Refresh skills"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
        {[
          { id: "catalog" as Tab, label: "Catalog", count: allSkills.length },
          {
            id: "proposals" as Tab,
            label: "Self-Evolution",
            count: pendingProposals.length,
          },
          { id: "create" as Tab, label: "Create New" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-colors flex-1 justify-center",
              tab === t.id
                ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm"
                : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
            )}
          >
            {t.label}
            {t.count !== undefined && t.count > 0 && (
              <span
                className={cn(
                  "text-xs px-1.5 py-0.5 rounded-full",
                  t.id === "proposals" && t.count > 0
                    ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                    : "bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300"
                )}
              >
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ===== CATALOG TAB ===== */}
      {tab === "catalog" && (
        <>
          {/* Phase filter + Search */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1">
              {(["all", "discover", "define", "develop", "deliver"] as PhaseFilter[]).map(
                (p) => (
                  <button
                    key={p}
                    onClick={() => setPhaseFilter(p)}
                    className={cn(
                      "px-3 py-1 rounded-md text-xs font-medium transition-colors capitalize",
                      phaseFilter === p
                        ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                    )}
                  >
                    {p}
                    {p !== "all" && (
                      <span className="ml-1 text-slate-400">
                        {phaseCounts[p] || 0}
                      </span>
                    )}
                  </button>
                )
              )}
            </div>
            <div className="relative flex-1">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                type="text"
                placeholder="Search skills..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              />
            </div>
          </div>

          {/* Skills list */}
          <div className="space-y-2">
            {filtered.map((skill) => {
              const health = healthMap[skill.name];
              const expanded = expandedSkill === skill.name;
              return (
                <div
                  key={skill.name}
                  className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden"
                >
                  {/* Skill row */}
                  <div className="w-full flex items-center gap-0">
                    <div
                      onClick={() =>
                        setExpandedSkill(expanded ? null : skill.name)
                      }
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setExpandedSkill(expanded ? null : skill.name); } }}
                      aria-expanded={expanded}
                      aria-label={`${skill.display_name} — ${skill.description}`}
                      className="flex-1 flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer min-w-0"
                    >
                      {expanded ? (
                        <ChevronDown size={14} className="text-slate-400 shrink-0" />
                      ) : (
                        <ChevronRight size={14} className="text-slate-400 shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm text-slate-900 dark:text-white truncate">
                            {skill.display_name}
                          </span>
                          <span
                            className={cn(
                              "text-[10px] px-1.5 py-0.5 rounded-full font-medium capitalize",
                              PHASE_COLORS[skill.phase] || ""
                            )}
                          >
                            {skill.phase}
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            v{skill.version}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 truncate mt-0.5">
                          {skill.description}
                        </p>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        {health && (
                          <div className="flex items-center gap-1.5">
                            <Activity size={12} className="text-slate-400" />
                            <HealthBadge score={health.health_score} />
                          </div>
                        )}
                        {health?.executions > 0 && (
                          <span className="text-[10px] text-slate-400">
                            {health.executions} runs
                          </span>
                        )}
                      </div>
                    </div>
                    <span
                      onClick={() => handleToggle(skill.name, skill.enabled)}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleToggle(skill.name, skill.enabled); } }}
                      role="switch"
                      tabIndex={0}
                      aria-checked={skill.enabled}
                      aria-label={skill.enabled ? `Disable ${skill.display_name}` : `Enable ${skill.display_name}`}
                      title={skill.enabled ? "Disable" : "Enable"}
                      className="text-slate-400 hover:text-slate-600 cursor-pointer shrink-0 px-4 py-3"
                    >
                      {skill.enabled ? (
                        <ToggleRight size={20} className="text-green-500" />
                      ) : (
                        <ToggleLeft size={20} />
                      )}
                    </span>
                  </div>

                  {/* Expanded detail */}
                  {expanded && (
                    <div className="border-t border-slate-100 dark:border-slate-700 px-4 py-4 space-y-4">
                      {/* Stats row */}
                      {health && (
                        <div className="grid grid-cols-5 gap-3">
                          {[
                            { label: "Health", value: `${(health.health_score * 100).toFixed(0)}%` },
                            { label: "Success Rate", value: `${(health.success_rate * 100).toFixed(0)}%` },
                            { label: "Quality", value: `${(health.avg_quality * 100).toFixed(0)}%` },
                            { label: "Completeness", value: `${(health.completeness * 100).toFixed(0)}%` },
                            {
                              label: "Last Used",
                              value: health.last_used
                                ? new Date(health.last_used).toLocaleDateString()
                                : "Never",
                            },
                          ].map((s) => (
                            <div key={s.label} className="text-center">
                              <p className="text-lg font-semibold text-slate-900 dark:text-white">
                                {s.value}
                              </p>
                              <p className="text-[10px] text-slate-400">
                                {s.label}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Prompts preview */}
                      {skill.plan_prompt && (
                        <div>
                          <p className="text-xs font-medium text-slate-500 mb-1">
                            Plan Prompt
                          </p>
                          <pre className="text-xs bg-slate-50 dark:bg-slate-900 rounded-lg p-3 max-h-32 overflow-y-auto whitespace-pre-wrap text-slate-700 dark:text-slate-300">
                            {skill.plan_prompt}
                          </pre>
                        </div>
                      )}
                      {skill.execute_prompt && (
                        <div>
                          <p className="text-xs font-medium text-slate-500 mb-1">
                            Execute Prompt
                          </p>
                          <pre className="text-xs bg-slate-50 dark:bg-slate-900 rounded-lg p-3 max-h-32 overflow-y-auto whitespace-pre-wrap text-slate-700 dark:text-slate-300">
                            {skill.execute_prompt}
                          </pre>
                        </div>
                      )}

                      {/* Changelog */}
                      {skill.changelog && skill.changelog.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-slate-500 mb-1">
                            Changelog
                          </p>
                          <div className="space-y-1 max-h-24 overflow-y-auto">
                            {skill.changelog
                              .slice()
                              .reverse()
                              .slice(0, 5)
                              .map((entry, i) => (
                                <div key={i} className="flex items-start gap-2 text-xs">
                                  <span className="font-mono text-slate-400 shrink-0">
                                    v{entry.version}
                                  </span>
                                  <span className="text-slate-600 dark:text-slate-400">
                                    {entry.changes}
                                  </span>
                                </div>
                              ))}
                          </div>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex gap-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                        <button
                          onClick={() => handleExecute(skill.name)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-reclaw-600 text-white text-xs font-medium hover:bg-reclaw-700"
                        >
                          <Play size={12} /> Run
                        </button>
                        <button
                          onClick={() =>
                            setEditingSkill(
                              editingSkill === skill.name ? null : skill.name
                            )
                          }
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-medium hover:bg-slate-200 dark:hover:bg-slate-600"
                        >
                          <Edit3 size={12} /> Edit
                        </button>
                        <button
                          onClick={() => handleDelete(skill.name)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-red-500 text-xs font-medium hover:bg-red-50 dark:hover:bg-red-900/20"
                        >
                          <Trash2 size={12} /> Delete
                        </button>
                      </div>

                      {/* Inline editor */}
                      {editingSkill === skill.name && (
                        <SkillEditor
                          skill={skill}
                          onSave={async (updates) => {
                            await skillsApi.update(skill.name, updates);
                            setEditingSkill(null);
                            await fetchSkills();
                          }}
                          onCancel={() => setEditingSkill(null)}
                        />
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {filtered.length === 0 && (
              <div className="text-center py-12 text-slate-400 text-sm">
                No skills match your filter.
              </div>
            )}
          </div>
        </>
      )}

      {/* ===== SELF-EVOLUTION TAB ===== */}
      {tab === "proposals" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={16} className="text-amber-500" />
            <h3 className="font-medium text-slate-900 dark:text-white">
              Self-Improvement Proposals
            </h3>
            <span className="text-xs text-slate-400">
              ReClaw analyzes skill performance and proposes improvements
            </span>
          </div>

          {pendingProposals.length === 0 && proposals.length === 0 && (
            <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
              <Sparkles
                size={32}
                className="mx-auto mb-3 text-slate-300"
              />
              <p className="text-slate-500 text-sm">
                No improvement proposals yet.
              </p>
              <p className="text-slate-400 text-xs mt-1">
                As skills are used, ReClaw will suggest improvements based on
                performance data.
              </p>
            </div>
          )}

          {/* Pending */}
          {pendingProposals.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase text-amber-600">
                Pending Review ({pendingProposals.length})
              </h4>
              {pendingProposals.map((p) => (
                <div
                  key={p.id}
                  className="bg-amber-50 dark:bg-amber-900/10 rounded-xl border border-amber-200 dark:border-amber-800 p-4 space-y-2"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="font-medium text-sm text-slate-900 dark:text-white">
                        {p.skill_name}
                      </span>
                      <span className="text-xs text-slate-400 ml-2">
                        .{p.field}
                      </span>
                    </div>
                    <span className="text-xs text-amber-600 font-medium">
                      {(p.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    {p.reason}
                  </p>
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-slate-400 mb-1">
                        Current
                      </p>
                      <pre className="text-sm bg-red-50 dark:bg-red-900/30 rounded p-2 min-h-[80px] max-h-64 overflow-y-auto whitespace-pre-wrap">
                        {p.current_value}
                      </pre>
                    </div>
                    <div>
                      <p className="text-xs text-slate-400 mb-1">
                        Proposed
                      </p>
                      <pre className="text-sm bg-green-50 dark:bg-green-900/30 rounded p-2 min-h-[80px] max-h-64 overflow-y-auto whitespace-pre-wrap">
                        {p.proposed_value}
                      </pre>
                    </div>
                  </div>
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={() => handleApprove(p.id)}
                      className="flex items-center gap-1 px-3 py-1 rounded-lg bg-green-600 text-white text-xs font-medium hover:bg-green-700"
                    >
                      <CheckCircle2 size={12} /> Approve
                    </button>
                    <button
                      onClick={() => handleReject(p.id)}
                      className="flex items-center gap-1 px-3 py-1 rounded-lg bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-medium hover:bg-slate-300"
                    >
                      <XCircle size={12} /> Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* History */}
          {proposals.filter((p) => p.status !== "pending").length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase text-slate-400">
                History
              </h4>
              {proposals
                .filter((p) => p.status !== "pending")
                .reverse()
                .slice(0, 20)
                .map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center gap-3 px-4 py-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700"
                  >
                    {p.status === "approved" ? (
                      <CheckCircle2 size={14} className="text-green-500 shrink-0" />
                    ) : (
                      <XCircle size={14} className="text-red-400 shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        {p.skill_name}
                      </span>
                      <span className="text-xs text-slate-400 ml-1">
                        .{p.field}
                      </span>
                    </div>
                    <span className="text-xs text-slate-400">
                      {p.reviewed_at
                        ? new Date(p.reviewed_at).toLocaleDateString()
                        : ""}
                    </span>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* ===== CREATE TAB ===== */}
      {tab === "create" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Plus size={16} className="text-reclaw-600" />
            <h3 className="font-medium text-slate-900 dark:text-white">
              Create New Skill
            </h3>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-500 mb-1 block">
                  Skill Name (slug)
                </label>
                <input
                  type="text"
                  placeholder="e.g., stakeholder-mapping"
                  value={newSkill.name}
                  onChange={(e) =>
                    setNewSkill({ ...newSkill, name: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 mb-1 block">
                  Display Name
                </label>
                <input
                  type="text"
                  placeholder="e.g., Stakeholder Mapping"
                  value={newSkill.display_name}
                  onChange={(e) =>
                    setNewSkill({ ...newSkill, display_name: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">
                Description
              </label>
              <textarea
                placeholder="What does this skill do?"
                value={newSkill.description}
                onChange={(e) =>
                  setNewSkill({ ...newSkill, description: e.target.value })
                }
                rows={2}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-500 mb-1 block">
                  Phase
                </label>
                <select
                  value={newSkill.phase}
                  onChange={(e) =>
                    setNewSkill({ ...newSkill, phase: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                >
                  <option value="discover">Discover</option>
                  <option value="define">Define</option>
                  <option value="develop">Develop</option>
                  <option value="deliver">Deliver</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 mb-1 block">
                  Type
                </label>
                <select
                  value={newSkill.skill_type}
                  onChange={(e) =>
                    setNewSkill({ ...newSkill, skill_type: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                >
                  <option value="analysis">Analysis</option>
                  <option value="generation">Generation</option>
                  <option value="evaluation">Evaluation</option>
                  <option value="synthesis">Synthesis</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">
                Plan Prompt
              </label>
              <textarea
                placeholder="Instructions for the planning phase..."
                value={newSkill.plan_prompt}
                onChange={(e) =>
                  setNewSkill({ ...newSkill, plan_prompt: e.target.value })
                }
                rows={4}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-none"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">
                Execute Prompt
              </label>
              <textarea
                placeholder="Instructions for the execution phase..."
                value={newSkill.execute_prompt}
                onChange={(e) =>
                  setNewSkill({ ...newSkill, execute_prompt: e.target.value })
                }
                rows={6}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-none"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">
                Output Schema
              </label>
              <textarea
                placeholder="Expected output format (JSON schema or description)..."
                value={newSkill.output_schema}
                onChange={(e) =>
                  setNewSkill({ ...newSkill, output_schema: e.target.value })
                }
                rows={3}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-none"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={handleCreate}
                disabled={!newSkill.name || !newSkill.display_name}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-reclaw-600 text-white text-sm font-medium hover:bg-reclaw-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Plus size={14} /> Create Skill
              </button>
              <button
                onClick={() => setTab("catalog")}
                className="px-4 py-2 rounded-lg text-slate-500 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- Inline Skill Editor ---------- */

function SkillEditor({
  skill,
  onSave,
  onCancel,
}: {
  skill: SkillData;
  onSave: (updates: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [desc, setDesc] = useState(skill.description);
  const [planPrompt, setPlanPrompt] = useState(skill.plan_prompt || "");
  const [execPrompt, setExecPrompt] = useState(skill.execute_prompt || "");
  const [changelog, setChangelog] = useState("");

  return (
    <div className="space-y-3 pt-3 border-t border-slate-100 dark:border-slate-700">
      <div>
        <label className="text-xs font-medium text-slate-500 mb-1 block">
          Description
        </label>
        <textarea
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-none"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-slate-500 mb-1 block">
          Plan Prompt
        </label>
        <textarea
          value={planPrompt}
          onChange={(e) => setPlanPrompt(e.target.value)}
          rows={4}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-none"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-slate-500 mb-1 block">
          Execute Prompt
        </label>
        <textarea
          value={execPrompt}
          onChange={(e) => setExecPrompt(e.target.value)}
          rows={6}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-none"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-slate-500 mb-1 block">
          Changelog note
        </label>
        <input
          type="text"
          placeholder="What changed?"
          value={changelog}
          onChange={(e) => setChangelog(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500"
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={() =>
            onSave({
              description: desc,
              plan_prompt: planPrompt,
              execute_prompt: execPrompt,
              changelog_entry: changelog,
            })
          }
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-reclaw-600 text-white text-xs font-medium hover:bg-reclaw-700"
        >
          <CheckCircle2 size={12} /> Save Changes
        </button>
        <button
          onClick={onCancel}
          className="px-3 py-1.5 rounded-lg text-slate-500 text-xs hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
