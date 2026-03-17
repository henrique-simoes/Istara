"use client";

import { useEffect, useState } from "react";
import { Save, Building2, FolderOpen, Shield, Eye, EyeOff } from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";
import ContextPreview from "@/components/common/ContextPreview";
import AutoSaveWarning from "@/components/common/AutoSaveWarning";

interface ContextSection {
  id: string;
  label: string;
  icon: typeof Building2;
  field: string;
  placeholder: string;
  description: string;
}

const SECTIONS: ContextSection[] = [
  {
    id: "company",
    label: "Company Context",
    icon: Building2,
    field: "company_context",
    placeholder:
      "Describe your company, product, users, culture, team norms...\n\nExample:\nAcme Corp — B2B SaaS for project management.\nTarget: mid-market teams (50-500 employees).\nCulture: data-driven, move fast, user-centric.\nKey stakeholders: PM (Maria), Eng Lead (James).",
    description:
      "Company-wide context inherited by all projects. Include product info, culture, team norms, and terminology.",
  },
  {
    id: "project",
    label: "Project Context",
    icon: FolderOpen,
    field: "project_context",
    placeholder:
      "Describe this specific research project...\n\nExample:\nRedesigning the onboarding flow to reduce churn.\nCurrent: 45% drop-off at step 3 (verification).\nGoal: Reduce to <20%. Timeline: Q1 2026.\nTarget users: New signups, ages 25-45.",
    description:
      "Project-specific context — research questions, goals, timeline, target users, current state.",
  },
  {
    id: "guardrails",
    label: "Guardrails & Instructions",
    icon: Shield,
    field: "guardrails",
    placeholder:
      "Set rules and boundaries for the agent...\n\nExample:\n- Always cite sources for claims\n- Flag if sample size < 5 for any conclusion\n- Don't contact participants directly\n- Use company terminology: 'workspace' not 'project'\n- Prioritize accessibility in all recommendations",
    description:
      "Rules, constraints, and instructions the agent must follow. These override default behavior.",
  },
];

export default function ContextEditor() {
  const { activeProjectId, projects, updateProject } = useProjectStore();
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [expandedSection, setExpandedSection] = useState<string>("company");
  const [hasChanges, setHasChanges] = useState(false);

  const project = projects.find((p) => p.id === activeProjectId);

  useEffect(() => {
    if (project) {
      setValues({
        company_context: project.company_context || "",
        project_context: project.project_context || "",
        guardrails: project.guardrails || "",
      });
    }
  }, [project]);

  const handleSave = async (field: string) => {
    if (!activeProjectId) return;
    setSaving(true);
    try {
      await updateProject(activeProjectId, { [field]: values[field] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error("Failed to save context:", e);
    }
    setSaving(false);
  };

  const handleSaveAll = async () => {
    if (!activeProjectId) return;
    setSaving(true);
    try {
      await updateProject(activeProjectId, values);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error("Failed to save context:", e);
    }
    setSaving(false);
  };

  if (!activeProjectId || !project) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <p>Select a project to edit context.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              📂 Project Context
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              These context layers shape how ReClaw understands and works on your project.
              The agent reads them before every task.
            </p>
          </div>
          <button
            onClick={handleSaveAll}
            disabled={saving}
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ml-4",
              saved
                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                : "bg-reclaw-600 text-white hover:bg-reclaw-700"
            )}
          >
            <Save size={14} />
            {saved ? "Saved!" : saving ? "Saving..." : "Save All"}
          </button>
        </div>

        {/* Context sections */}
        {SECTIONS.map((section) => {
          const isExpanded = expandedSection === section.id;
          const charCount = (values[section.field] || "").length;

          return (
            <div
              key={section.id}
              className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden"
            >
              {/* Section header */}
              <button
                onClick={() => setExpandedSection(isExpanded ? "" : section.id)}
                className="flex items-center justify-between w-full p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <section.icon size={20} className="text-reclaw-600" />
                  <div className="text-left">
                    <h3 className="font-medium text-slate-900 dark:text-white">
                      {section.label}
                    </h3>
                    <p className="text-xs text-slate-500">{section.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {charCount > 0 && (
                    <span className="text-xs bg-reclaw-100 dark:bg-reclaw-900/30 text-reclaw-700 dark:text-reclaw-400 px-2 py-0.5 rounded-full">
                      {charCount} chars
                    </span>
                  )}
                  {isExpanded ? <EyeOff size={16} className="text-slate-400" /> : <Eye size={16} className="text-slate-400" />}
                </div>
              </button>

              {/* Editor */}
              {isExpanded && (
                <div className="border-t border-slate-200 dark:border-slate-700 p-4">
                  <textarea
                    value={values[section.field] || ""}
                    onChange={(e) =>
                      setValues({ ...values, [section.field]: e.target.value })
                    }
                    placeholder={section.placeholder}
                    rows={8}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 p-3 text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-reclaw-500 focus:border-transparent resize-y"
                  />
                  <div className="flex justify-end mt-2">
                    <button
                      onClick={() => handleSave(section.field)}
                      disabled={saving}
                      className="text-sm text-reclaw-600 hover:text-reclaw-700 font-medium"
                    >
                      {saving ? "Saving..." : `Save ${section.label}`}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Context preview — "What I know" */}
        <ContextPreview />

        {/* Unsaved changes warning */}
        <AutoSaveWarning hasUnsavedChanges={hasChanges} />

        {/* How it works */}
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 text-sm text-slate-500 dark:text-slate-400">
          <p className="font-medium text-slate-700 dark:text-slate-300 mb-2">
            How context layers work:
          </p>
          <div className="space-y-1">
            <p>
              🏢 <strong>Company</strong> → inherited by all projects (product, culture,
              terminology)
            </p>
            <p>
              📁 <strong>Project</strong> → specific to this research (goals, questions,
              users, timeline)
            </p>
            <p>
              🛡️ <strong>Guardrails</strong> → rules the agent must follow (cite sources,
              flag small samples, etc.)
            </p>
            <p className="mt-2 italic">
              The agent composes all three layers before every task, so be specific but
              concise.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
