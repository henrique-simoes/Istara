"use client";

import { useState } from "react";
import { Save, X, Bot, User, Zap } from "lucide-react";
import { useTaskStore } from "@/stores/taskStore";
import { cn } from "@/lib/utils";
import type { Task } from "@/lib/types";

// Common UXR skills for the dropdown
const SKILL_OPTIONS = [
  { value: "", label: "Auto-detect (from title)" },
  { value: "user-interviews", label: "📋 User Interviews" },
  { value: "thematic-analysis", label: "🏷️ Thematic Analysis" },
  { value: "affinity-mapping", label: "🗂️ Affinity Mapping" },
  { value: "persona-creation", label: "👤 Persona Creation" },
  { value: "journey-mapping", label: "🗺️ Journey Mapping" },
  { value: "usability-testing", label: "🧪 Usability Testing" },
  { value: "competitive-analysis", label: "🔍 Competitive Analysis" },
  { value: "survey-design", label: "📝 Survey Design" },
  { value: "heuristic-evaluation", label: "✅ Heuristic Evaluation" },
  { value: "research-synthesis", label: "📊 Research Synthesis" },
  { value: "survey-generator", label: "📋 Survey Generator" },
  { value: "interview-question-generator", label: "❓ Interview Questions" },
  { value: "taxonomy-generator", label: "🏷️ Taxonomy Generator" },
  { value: "kappa-thematic-analysis", label: "📏 Kappa Analysis" },
  { value: "survey-ai-detection", label: "🤖 AI Detection" },
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
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateTask(task.id, {
        title,
        description,
        skill_name: skillName,
        user_context: userContext,
      });
      onClose();
    } catch (e) {
      console.error("Failed to save task:", e);
    }
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl max-w-lg w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
          <h3 className="font-semibold text-slate-900 dark:text-white">Edit Task</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800">
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

          {/* User context */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1 flex items-center gap-1">
              <User size={12} /> Additional Context for Agent
            </label>
            <textarea
              value={userContext}
              onChange={(e) => setUserContext(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500 resize-y font-mono"
              placeholder="Give the agent specific instructions, focus areas, or constraints..."
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
        <div className="flex justify-end gap-2 p-4 border-t border-slate-200 dark:border-slate-700">
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
