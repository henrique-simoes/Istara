"use client";

import { useState } from "react";
import { useTourStore } from "@/stores/tourStore";
import { useProjectStore } from "@/stores/projectStore";
import { FolderOpen, Sparkles } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TourInlineStepProps {
  step: number;
}

export default function TourInlineStep({ step }: TourInlineStepProps) {
  const tour = useTourStore();
  const { createProject } = useProjectStore();

  // Step 0 state — folder selection
  const [folderPath, setFolderPath] = useState(tour.folderPath);
  // Step 1 state — project creation
  const [projectName, setProjectName] = useState("");
  const [projectDesc, setProjectDesc] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFolderContinue = () => {
    if (!folderPath.trim()) {
      setError("Enter a folder path to store your research files.");
      return;
    }
    tour.setFolderPath(folderPath.trim());
    tour.nextStep();
  };

  const handleCreateProject = async () => {
    if (!projectName.trim()) {
      setError("Give your project a name.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const project = await createProject(projectName.trim(), projectDesc.trim());

      // Link the folder to the project
      if (tour.folderPath) {
        const token = localStorage.getItem("istara_token");
        await fetch(`${API_BASE}/api/projects/${project.id}/link-folder`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ folder_path: tour.folderPath }),
        });
      }

      tour.setProjectCreated(project.id);
      tour.nextStep();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4">
      <div className="w-full max-w-lg">
        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 p-8">
          {/* Logo */}
          <div className="text-center mb-6">
            <div className="text-5xl mb-3">🐾</div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
              {step === 0 ? "Welcome to Istara" : "Create Your Project"}
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              {step === 0
                ? "Let's set up your research workspace in a few quick steps."
                : "This project will be linked to your research folder."}
            </p>
          </div>

          {/* Step 0: Folder Selection */}
          {step === 0 && (
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                  <FolderOpen size={14} className="inline mr-1.5" />
                  Research Folder
                </label>
                <input
                  type="text"
                  value={folderPath}
                  onChange={(e) => { setFolderPath(e.target.value); setError(""); }}
                  placeholder="/Users/you/Research/ProjectName"
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-istara-500 transition text-sm"
                />
                <p className="mt-1.5 text-xs text-slate-400 dark:text-slate-500">
                  Point to a local folder, Google Drive, Dropbox, or OneDrive folder.
                  Istara will watch it for new files automatically.
                </p>
              </div>

              {error && (
                <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}

              <div className="flex items-center justify-between">
                <button
                  onClick={tour.skipTour}
                  className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition"
                >
                  Skip setup
                </button>
                <button
                  onClick={handleFolderContinue}
                  disabled={!folderPath.trim()}
                  className="px-6 py-2.5 rounded-lg bg-istara-600 hover:bg-istara-700 text-white font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* Step 1: Project Creation */}
          {step === 1 && (
            <div className="space-y-5">
              {tour.folderPath && (
                <div className="rounded-lg bg-istara-50 dark:bg-istara-900/20 border border-istara-200 dark:border-istara-800 px-3 py-2 text-xs text-istara-700 dark:text-istara-400 flex items-center gap-2">
                  <FolderOpen size={14} />
                  <span className="font-mono truncate">{tour.folderPath}</span>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                  <Sparkles size={14} className="inline mr-1.5" />
                  Project Name
                </label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => { setProjectName(e.target.value); setError(""); }}
                  placeholder="e.g. Q2 User Research, Mobile App Redesign"
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-istara-500 transition text-sm"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                  Description (optional)
                </label>
                <textarea
                  value={projectDesc}
                  onChange={(e) => setProjectDesc(e.target.value)}
                  placeholder="What are you researching?"
                  rows={2}
                  className="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-istara-500 transition text-sm"
                />
              </div>

              {error && (
                <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}

              <div className="flex items-center justify-between">
                <button
                  onClick={tour.skipTour}
                  className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition"
                >
                  Skip setup
                </button>
                <button
                  onClick={handleCreateProject}
                  disabled={loading || !projectName.trim()}
                  className="px-6 py-2.5 rounded-lg bg-istara-600 hover:bg-istara-700 text-white font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? "Creating..." : "Create Project"}
                </button>
              </div>
            </div>
          )}

          {/* Progress dots */}
          <div className="flex justify-center gap-2 mt-6">
            <div className={`w-2 h-2 rounded-full ${step === 0 ? "bg-istara-500" : "bg-slate-300 dark:bg-slate-600"}`} />
            <div className={`w-2 h-2 rounded-full ${step === 1 ? "bg-istara-500" : "bg-slate-300 dark:bg-slate-600"}`} />
          </div>
        </div>
      </div>
    </div>
  );
}
