"use client";

import { useState, useRef } from "react";
import {
  Sparkles,
  FolderPlus,
  Upload,
  ArrowRight,
  ArrowLeft,
  Check,
  Building2,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { files as filesApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface OnboardingWizardProps {
  onComplete: () => void;
}

const STEPS = [
  { id: "welcome", title: "Welcome to ReClaw", icon: Sparkles },
  { id: "project", title: "Create Your First Project", icon: FolderPlus },
  { id: "context", title: "Set Your Context", icon: Building2 },
  { id: "upload", title: "Upload Research Data", icon: Upload },
];

export default function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState(0);
  const [projectName, setProjectName] = useState("");
  const [companyContext, setCompanyContext] = useState("");
  const [projectContext, setProjectContext] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { createProject, updateProject } = useProjectStore();
  const [createdProjectId, setCreatedProjectId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleCreateProject = async () => {
    if (!projectName.trim()) return;
    setError(null);
    try {
      const project = await createProject(projectName.trim());
      setCreatedProjectId(project.id);
      setStep(2);
    } catch (e: any) {
      setError(e.message || "Failed to create project. Is the backend running?");
    }
  };

  const handleSaveContext = async () => {
    if (createdProjectId) {
      const updates: Record<string, string> = {};
      if (companyContext.trim()) updates.company_context = companyContext;
      if (projectContext.trim()) updates.project_context = projectContext;
      if (Object.keys(updates).length > 0) {
        await updateProject(createdProjectId, updates);
      }
    }
    setStep(3);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || !createdProjectId) return;
    setUploading(true);

    for (const file of Array.from(fileList)) {
      try {
        await filesApi.upload(createdProjectId, file);
        setUploadedFiles((prev) => [...prev, file.name]);
      } catch (err) {
        console.error("Upload failed:", err);
      }
    }
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const currentStep = STEPS[step];

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden">
        {/* Progress */}
        <div className="flex gap-1 p-4 pb-0">
          {STEPS.map((s, i) => (
            <div
              key={s.id}
              className={cn(
                "h-1 flex-1 rounded-full transition-colors",
                i <= step ? "bg-reclaw-500" : "bg-slate-200 dark:bg-slate-700"
              )}
            />
          ))}
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Step 0: Welcome */}
          {step === 0 && (
            <div className="text-center">
              <span className="text-5xl block mb-4">🐾</span>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
                Welcome to ReClaw
              </h2>
              <p className="text-slate-500 mb-2">
                Your local-first AI agent for UX Research.
              </p>
              <p className="text-sm text-slate-400 mb-6">
                Let's set you up in 3 quick steps. Your data never leaves your machine.
              </p>

              <div className="grid grid-cols-3 gap-3 mb-6 text-center">
                {[
                  { emoji: "📁", label: "Create a project" },
                  { emoji: "📄", label: "Upload research" },
                  { emoji: "💡", label: "Get insights" },
                ].map((item) => (
                  <div key={item.label} className="bg-slate-50 dark:bg-slate-800 rounded-xl p-3">
                    <span className="text-2xl">{item.emoji}</span>
                    <p className="text-xs text-slate-500 mt-1">{item.label}</p>
                  </div>
                ))}
              </div>

              <button
                onClick={() => setStep(1)}
                className="flex items-center gap-2 mx-auto px-6 py-3 bg-reclaw-600 text-white rounded-xl hover:bg-reclaw-700 font-medium"
              >
                Get Started <ArrowRight size={16} />
              </button>
            </div>
          )}

          {/* Step 1: Create Project */}
          {step === 1 && (
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-1">
                Create Your First Project
              </h2>
              <p className="text-sm text-slate-500 mb-4">
                Projects organize your research around the Double Diamond framework.
              </p>

              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Project Name
              </label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="e.g., Onboarding Redesign Study"
                onKeyDown={(e) => e.key === "Enter" && handleCreateProject()}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500 mb-4"
                autoFocus
              />

              {error && (
                <div className="mb-3 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-sm text-red-600 dark:text-red-400">
                  ⚠️ {error}
                </div>
              )}

              <div className="flex justify-between">
                <button
                  onClick={() => setStep(0)}
                  className="flex items-center gap-1 text-sm text-slate-400 hover:text-slate-600"
                >
                  <ArrowLeft size={14} /> Back
                </button>
                <button
                  onClick={handleCreateProject}
                  disabled={!projectName.trim()}
                  className={cn(
                    "flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm",
                    projectName.trim()
                      ? "bg-reclaw-600 text-white hover:bg-reclaw-700"
                      : "bg-slate-200 text-slate-400 cursor-not-allowed"
                  )}
                >
                  Create Project <ArrowRight size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Context */}
          {step === 2 && (
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-1">
                Set Your Context
              </h2>
              <p className="text-sm text-slate-500 mb-4">
                This helps the agent understand your company and research goals. You can edit these later.
              </p>

              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Company / Product <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <textarea
                value={companyContext}
                onChange={(e) => setCompanyContext(e.target.value)}
                placeholder="e.g., B2B SaaS for project management, targeting mid-market teams..."
                rows={2}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500 mb-3"
              />

              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Research Goals <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <textarea
                value={projectContext}
                onChange={(e) => setProjectContext(e.target.value)}
                placeholder="e.g., Understand why users drop off during onboarding. Goal: reduce churn by 20%..."
                rows={2}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-reclaw-500 mb-4"
              />

              <div className="flex justify-between">
                <button
                  onClick={() => setStep(1)}
                  className="flex items-center gap-1 text-sm text-slate-400 hover:text-slate-600"
                >
                  <ArrowLeft size={14} /> Back
                </button>
                <button
                  onClick={handleSaveContext}
                  className="flex items-center gap-2 px-5 py-2.5 bg-reclaw-600 text-white rounded-xl hover:bg-reclaw-700 font-medium text-sm"
                >
                  {companyContext || projectContext ? "Save & Continue" : "Skip for Now"} <ArrowRight size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Upload */}
          {step === 3 && (
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-1">
                Upload Research Data
              </h2>
              <p className="text-sm text-slate-500 mb-4">
                Drop interview transcripts, survey data, notes — anything you want the agent to analyze.
              </p>

              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".txt,.pdf,.docx,.csv,.md"
                onChange={handleFileUpload}
                className="hidden"
              />

              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="w-full border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-8 text-center hover:border-reclaw-400 hover:bg-reclaw-50 dark:hover:bg-reclaw-900/10 transition-colors mb-3"
              >
                <Upload size={24} className="mx-auto text-slate-400 mb-2" />
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  {uploading ? "Uploading..." : "Click to upload files"}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  PDF, DOCX, TXT, CSV, MD
                </p>
              </button>

              {uploadedFiles.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-medium text-slate-500 mb-1">Uploaded:</p>
                  {uploadedFiles.map((f) => (
                    <div key={f} className="flex items-center gap-2 text-xs text-reclaw-600 py-0.5">
                      <Check size={12} /> {f}
                    </div>
                  ))}
                </div>
              )}

              <div className="flex justify-between">
                <button
                  onClick={() => setStep(2)}
                  className="flex items-center gap-1 text-sm text-slate-400 hover:text-slate-600"
                >
                  <ArrowLeft size={14} /> Back
                </button>
                <button
                  onClick={onComplete}
                  className="flex items-center gap-2 px-5 py-2.5 bg-reclaw-600 text-white rounded-xl hover:bg-reclaw-700 font-medium text-sm"
                >
                  {uploadedFiles.length > 0 ? "Start Researching" : "Skip & Explore"} <Sparkles size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
