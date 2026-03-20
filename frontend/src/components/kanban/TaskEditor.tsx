"use client";

import { useState } from "react";
import { Save, X, Bot, User, Zap, FileStack, Globe, ClipboardList, Plus, Trash2 } from "lucide-react";
import { useTaskStore } from "@/stores/taskStore";
import { cn } from "@/lib/utils";
import type { Task } from "@/lib/types";

// Common UXR skills for the dropdown
const SKILL_OPTIONS = [
  { value: "", label: "Auto-detect (from title)" },
  { value: "user-interviews", label: "User Interviews" },
  { value: "thematic-analysis", label: "Thematic Analysis" },
  { value: "affinity-mapping", label: "Affinity Mapping" },
  { value: "persona-creation", label: "Persona Creation" },
  { value: "journey-mapping", label: "Journey Mapping" },
  { value: "usability-testing", label: "Usability Testing" },
  { value: "competitive-analysis", label: "Competitive Analysis" },
  { value: "survey-design", label: "Survey Design" },
  { value: "heuristic-evaluation", label: "Heuristic Evaluation" },
  { value: "research-synthesis", label: "Research Synthesis" },
  { value: "survey-generator", label: "Survey Generator" },
  { value: "interview-question-generator", label: "Interview Questions" },
  { value: "taxonomy-generator", label: "Taxonomy Generator" },
  { value: "kappa-thematic-analysis", label: "Kappa Analysis" },
  { value: "survey-ai-detection", label: "AI Detection" },
];

interface TaskEditorProps {
  task: Task;
  onClose: () => void;
}

export default function TaskEditor({ task, onClose }: TaskEditorProps) {
  const { updateTask } = useTaskStore();
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description);
  const [skillName, setSkillName] = useState(task.skill_name);
  const [userContext, setUserContext] = useState(task.user_context);
  const [instructions, setInstructions] = useState(task.instructions || "");
  const [urls, setUrls] = useState<string[]>(task.urls || []);
  const [newUrl, setNewUrl] = useState("");
  const [saving, setSaving] = useState(false);

  const inputDocs = task.input_document_ids || [];
  const outputDocs = task.output_document_ids || [];

  const handleAddUrl = () => {
    const trimmed = newUrl.trim();
    if (trimmed && !urls.includes(trimmed)) {
      setUrls([...urls, trimmed]);
      setNewUrl("");
    }
  };

  const handleRemoveUrl = (idx: number) => {
    setUrls(urls.filter((_, i) => i !== idx));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateTask(task.id, {
        title,
        description,
        skill_name: skillName,
        user_context: userContext,
        instructions,
        urls,
      });
      onClose();
    } catch (e) {
      console.error("Failed to save task:", e);
    }
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700 sticky top-0 bg-white dark:bg-slate-900 z-10">
          <h3 className="font-semibold text-slate-900 dark:text-white">Edit Task</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Close editor">
            <X size={16} className="text-slate-400" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          {/* Title */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-y"
              placeholder="What should the agent do?"
            />
          </div>

          {/* Skill selector */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
              <Zap size={12} /> Skill
            </label>
            <select
              value={skillName}
              onChange={(e) => setSkillName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500"
            >
              {SKILL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Select a skill or let the agent auto-detect from the task title.
            </p>
          </div>

          {/* Instructions */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
              <ClipboardList size={12} /> Specific Instructions
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-y"
              placeholder="Step-by-step instructions for the agent (e.g., 'Focus on onboarding flows' or 'Compare only pricing pages')..."
            />
          </div>

          {/* URLs */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
              <Globe size={12} /> URLs to Fetch
            </label>
            {urls.length > 0 && (
              <div className="space-y-1 mb-2">
                {urls.map((url, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="flex-1 truncate text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800 px-2 py-1 rounded">
                      {url}
                    </span>
                    <button
                      onClick={() => handleRemoveUrl(i)}
                      className="p-1 text-red-400 hover:text-red-500"
                      aria-label={`Remove URL ${url}`}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="flex gap-2">
              <input
                type="url"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleAddUrl(); } }}
                placeholder="https://example.com/page-to-analyze"
                className="flex-1 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              />
              <button
                onClick={handleAddUrl}
                disabled={!newUrl.trim()}
                className="px-2 py-1.5 text-xs rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 disabled:opacity-40"
                aria-label="Add URL"
              >
                <Plus size={14} />
              </button>
            </div>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Add web addresses for the agent to fetch and analyze.
            </p>
          </div>

          {/* Document attachments (read-only summary) */}
          {(inputDocs.length > 0 || outputDocs.length > 0) && (
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
                <FileStack size={12} /> Attached Documents
              </label>
              <div className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800/50 text-xs space-y-1">
                {inputDocs.length > 0 && (
                  <p className="text-slate-600 dark:text-slate-400">
                    <span className="font-medium">Input:</span> {inputDocs.length} document(s)
                  </p>
                )}
                {outputDocs.length > 0 && (
                  <p className="text-slate-600 dark:text-slate-400">
                    <span className="font-medium">Output:</span> {outputDocs.length} document(s)
                  </p>
                )}
                <p className="text-[10px] text-slate-400">
                  Attach documents via Chat or the Documents view.
                </p>
              </div>
            </div>
          )}

          {/* User context */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
              <User size={12} /> Additional Context for Agent
            </label>
            <textarea
              value={userContext}
              onChange={(e) => setUserContext(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-y font-mono"
              placeholder="Give the agent project-specific context or constraints..."
            />
          </div>

          {/* Agent notes (read-only) */}
          {task.agent_notes && (
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
                <Bot size={12} /> Agent Notes
              </label>
              <div className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800/50 text-xs text-slate-600 dark:text-slate-400 max-h-24 overflow-y-auto">
                {task.agent_notes}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t border-slate-200 dark:border-slate-700 sticky bottom-0 bg-white dark:bg-slate-900">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !title.trim()}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-reclaw-600 text-white hover:bg-reclaw-700 disabled:opacity-50 font-medium"
          >
            <Save size={14} />
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
