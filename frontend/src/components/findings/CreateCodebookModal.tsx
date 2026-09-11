"use client";

import React, { useState } from "react";
import { X, Plus, Trash2, BookPlus, Sparkles, AlertCircle, Loader2 } from "lucide-react";
import { codebookVersions as codebookApi } from "@/lib/api";
import type { CodebookVersionType, CodeEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

interface CreateCodebookModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onCreated: (newCodebook: CodebookVersionType) => void;
}

interface DraftCode {
  id: string;
  label: string;
  parent_theme: string;
  brief_definition: string;
  full_definition: string;
  exclusion_criteria: string;
  typical_example: string;
}

const TEMPLATE_CODES: DraftCode[] = [
  {
    id: "code-1",
    label: "user_friction",
    parent_theme: "Usability Tensions",
    brief_definition: "User encounters an obstacle, confusion, or slowdown in the primary flow.",
    full_definition: "Includes hesitation > 5s, error messages, or expressions of confusion regarding controls.",
    exclusion_criteria: "Excludes general device hardware issues or slow internet connections.",
    typical_example: "I couldn't figure out where the save button was located.",
  },
  {
    id: "code-2",
    label: "workaround_strategy",
    parent_theme: "Behavioral Adaptations",
    brief_definition: "User devises an alternate manual method to accomplish what the system failed to do.",
    full_definition: "Includes taking external notes, switching tabs to third-party tools, or manual retyping.",
    exclusion_criteria: "Excludes intended multi-tool workflows documented in help docs.",
    typical_example: "I just copy the text into Google Docs so I don't lose my work.",
  },
  {
    id: "code-3",
    label: "value_driver",
    parent_theme: "Value Perception",
    brief_definition: "User expresses satisfaction or perceives high tangible value from a capability.",
    full_definition: "Direct quotes expressing delight, time saved, or willingness to recommend.",
    exclusion_criteria: "Excludes neutral factual statements.",
    typical_example: "This report usually takes me two days and I finished it in 15 minutes.",
  },
];

export default function CreateCodebookModal({
  projectId,
  isOpen,
  onClose,
  onCreated,
}: CreateCodebookModalProps) {
  const [version, setVersion] = useState("1.0.0");
  const [methodology, setMethodology] = useState<"codebook_ta" | "reflexive_ta" | "grounded_theory">(
    "codebook_ta"
  );
  const [changeLog, setChangeLog] = useState("");
  const [codes, setCodes] = useState<DraftCode[]>([
    {
      id: "code-init",
      label: "",
      parent_theme: "",
      brief_definition: "",
      full_definition: "",
      exclusion_criteria: "",
      typical_example: "",
    },
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAddCode = () => {
    setCodes((prev) => [
      ...prev,
      {
        id: `code-${Date.now()}-${prev.length}`,
        label: "",
        parent_theme: "",
        brief_definition: "",
        full_definition: "",
        exclusion_criteria: "",
        typical_example: "",
      },
    ]);
  };

  const handleRemoveCode = (id: string) => {
    if (codes.length === 1) return;
    setCodes((prev) => prev.filter((c) => c.id !== id));
  };

  const handleCodeChange = (id: string, field: keyof DraftCode, value: string) => {
    setCodes((prev) =>
      prev.map((c) => (c.id === id ? { ...c, [field]: value } : c))
    );
  };

  const handleApplyTemplate = () => {
    setCodes(TEMPLATE_CODES);
    if (!changeLog) {
      setChangeLog("Initial baseline qualitative coding taxonomy.");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const validCodes = codes.filter((c) => c.label.trim().length > 0);
    if (validCodes.length === 0) {
      setError("Please add at least one code with a name / label.");
      return;
    }

    setSubmitting(true);
    try {
      const formattedCodes: CodeEntry[] = validCodes.map((c) => ({
        code_id: c.label.trim().toLowerCase().replace(/\s+/g, "_"),
        label: c.label.trim(),
        parent_theme: c.parent_theme.trim() || null,
        brief_definition: c.brief_definition.trim(),
        full_definition: c.full_definition.trim() || c.brief_definition.trim(),
        exclusion_criteria: c.exclusion_criteria.trim(),
        typical_example: c.typical_example.trim(),
        boundary_example: "",
        coding_method: methodology,
        frequency: 0,
      }));

      const newCodebook = await codebookApi.create({
        project_id: projectId,
        version: version.trim() || "1.0.0",
        methodology,
        change_log: changeLog.trim() || "Created via Codebook Studio.",
        codes: formattedCodes,
      });

      onCreated(newCodebook);
      onClose();
    } catch (err) {
      console.error("Failed to create codebook:", err);
      setError(err instanceof Error ? err.message : "Failed to create codebook.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 w-full max-w-3xl rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookPlus className="text-istara-600 dark:text-istara-400" size={20} />
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-base">
                Create Qualitative Codebook
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Ground research tasks and multi-model coding in a validated qualitative taxonomy.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-md"
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-xs text-red-700 dark:text-red-300 flex items-center gap-2">
              <AlertCircle size={15} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Core Configuration */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Version Tag
              </label>
              <input
                type="text"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="e.g. 1.0.0 or CoreTaxonomy-v1"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs focus:ring-2 focus:ring-istara-500 focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Qualitative Methodology
              </label>
              <select
                value={methodology}
                onChange={(e) =>
                  setMethodology(e.target.value as "codebook_ta" | "reflexive_ta" | "grounded_theory")
                }
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs focus:ring-2 focus:ring-istara-500 focus:outline-none"
              >
                <option value="codebook_ta">Codebook TA (Deductive / Structured Coding)</option>
                <option value="reflexive_ta">Reflexive TA (Inductive / Interpretive Themes)</option>
                <option value="grounded_theory">Grounded Theory (Open / Axial / Selective)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Description & Change Log
            </label>
            <input
              type="text"
              value={changeLog}
              onChange={(e) => setChangeLog(e.target.value)}
              placeholder="e.g. Initial codebook for usability testing and interview analysis"
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs focus:ring-2 focus:ring-istara-500 focus:outline-none"
            />
          </div>

          {/* Codes Definition Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Codes & Definitions ({codes.length})
                </h4>
                <p className="text-[11px] text-slate-400">
                  Define code boundaries, criteria, and exemplar quotes to maintain high inter-coder reliability.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleApplyTemplate}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 hover:bg-purple-100 transition-colors"
                >
                  <Sparkles size={12} /> Load Starter Template
                </button>
                <button
                  type="button"
                  onClick={handleAddCode}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium bg-istara-50 dark:bg-istara-900/30 text-istara-700 dark:text-istara-300 border border-istara-200 dark:border-istara-800 hover:bg-istara-100 transition-colors"
                >
                  <Plus size={12} /> Add Code
                </button>
              </div>
            </div>

            <div className="space-y-3">
              {codes.map((code, index) => (
                <div
                  key={code.id}
                  className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/40 space-y-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-[10px] font-mono font-bold text-slate-400">
                      #{index + 1}
                    </span>
                    <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <input
                        type="text"
                        value={code.label}
                        onChange={(e) => handleCodeChange(code.id, "label", e.target.value)}
                        placeholder="Code Name (e.g. pain_point)"
                        className="px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-mono font-medium focus:ring-1 focus:ring-istara-500 focus:outline-none"
                        required
                      />
                      <input
                        type="text"
                        value={code.parent_theme}
                        onChange={(e) => handleCodeChange(code.id, "parent_theme", e.target.value)}
                        placeholder="Category / Theme (optional)"
                        className="px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs focus:ring-1 focus:ring-istara-500 focus:outline-none"
                      />
                    </div>
                    {codes.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveCode(code.id)}
                        className="text-slate-400 hover:text-red-500 p-1"
                        aria-label="Remove code"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    <div>
                      <input
                        type="text"
                        value={code.brief_definition}
                        onChange={(e) =>
                          handleCodeChange(code.id, "brief_definition", e.target.value)
                        }
                        placeholder="Brief definition..."
                        className="w-full px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs focus:ring-1 focus:ring-istara-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <input
                        type="text"
                        value={code.full_definition}
                        onChange={(e) =>
                          handleCodeChange(code.id, "full_definition", e.target.value)
                        }
                        placeholder="Inclusion criteria..."
                        className="w-full px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs focus:ring-1 focus:ring-istara-500 focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    <div>
                      <input
                        type="text"
                        value={code.exclusion_criteria}
                        onChange={(e) =>
                          handleCodeChange(code.id, "exclusion_criteria", e.target.value)
                        }
                        placeholder="Exclusion criteria..."
                        className="w-full px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs focus:ring-1 focus:ring-istara-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <input
                        type="text"
                        value={code.typical_example}
                        onChange={(e) =>
                          handleCodeChange(code.id, "typical_example", e.target.value)
                        }
                        placeholder="Exemplar quote..."
                        className="w-full px-2.5 py-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs focus:ring-1 focus:ring-istara-500 focus:outline-none"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Footer actions inside form */}
          <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-istara-600 hover:bg-istara-700 text-white transition-colors shadow-sm disabled:opacity-50"
            >
              {submitting && <Loader2 size={13} className="animate-spin" />}
              {submitting ? "Creating..." : "Save & Activate Codebook"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
