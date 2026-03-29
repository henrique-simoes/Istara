"use client";

import { useState } from "react";
import { FolderOpen, CheckCircle2, AlertTriangle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FolderLinkStepProps {
  projectId: string | null;
}

/**
 * Onboarding step: optionally link an external research folder.
 * Supports Google Drive, Dropbox, OneDrive, or any local folder.
 */
export default function FolderLinkStep({ projectId }: FolderLinkStepProps) {
  const [folderPath, setFolderPath] = useState("");
  const [linking, setLinking] = useState(false);
  const [linked, setLinked] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLink = async () => {
    if (!folderPath.trim() || !projectId) return;
    setLinking(true);
    setError(null);
    try {
      const token = localStorage.getItem("reclaw_token");
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/link-folder`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ folder_path: folderPath.trim() }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Failed to link folder" }));
        throw new Error(data.detail);
      }
      setLinked(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLinking(false);
    }
  };

  if (linked) {
    return (
      <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
        <CheckCircle2 size={24} className="text-green-600 shrink-0" />
        <div>
          <p className="text-sm font-medium text-green-800 dark:text-green-300">
            Folder linked successfully
          </p>
          <p className="text-xs text-green-600 dark:text-green-400 mt-0.5 font-mono truncate">
            {folderPath}
          </p>
          <p className="text-xs text-green-600 dark:text-green-400 mt-1">
            Files will be monitored automatically. New files appear in Documents.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
        Already have a research folder? Point ReClaw at it — files will be monitored and auto-analyzed.
        Works with <strong>Google Drive</strong>, <strong>Dropbox</strong>, <strong>OneDrive</strong>, or any local folder.
      </p>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <FolderOpen size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={folderPath}
            onChange={(e) => { setFolderPath(e.target.value); setError(null); }}
            onKeyDown={(e) => e.key === "Enter" && handleLink()}
            placeholder="/Users/you/Google Drive/UX Research"
            className="w-full pl-10 pr-3 py-2.5 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-reclaw-500 transition"
            aria-label="Folder path"
          />
        </div>
        <button
          onClick={handleLink}
          disabled={!folderPath.trim() || !projectId || linking}
          className="px-4 py-2.5 text-sm font-medium rounded-lg bg-reclaw-600 text-white hover:bg-reclaw-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {linking ? "Linking..." : "Link"}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-xs text-red-600 dark:text-red-400">
          <AlertTriangle size={12} />
          {error}
        </div>
      )}

      <p className="text-xs text-slate-400">
        This is optional. You can also upload files manually or link a folder later in Documents.
      </p>
    </div>
  );
}
