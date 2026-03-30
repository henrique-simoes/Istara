"use client";

import { useEffect, useState } from "react";
import { LayoutGrid, Trash2, ExternalLink, X, Monitor, Smartphone, Tablet, Globe, Loader2 } from "lucide-react";
import { useInterfacesStore } from "@/stores/interfacesStore";
import { useProjectStore } from "@/stores/projectStore";
import { interfaces as interfacesApi } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import ScreenPreview from "./ScreenPreview";

const DEVICE_ICONS: Record<string, any> = {
  MOBILE: Smartphone,
  DESKTOP: Monitor,
  TABLET: Tablet,
  AGNOSTIC: Globe,
};

const STATUS_COLORS: Record<string, string> = {
  generating: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  ready: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  error: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

export default function ScreensGalleryTab() {
  const { screens, loading, fetchScreens } = useInterfacesStore();
  const { activeProjectId } = useProjectStore();
  const [selectedScreen, setSelectedScreen] = useState<any>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    if (activeProjectId) {
      fetchScreens(activeProjectId);
    }
  }, [activeProjectId, fetchScreens]);

  const handleDelete = async (screenId: string) => {
    setDeleting(screenId);
    try {
      await interfacesApi.screens.delete(screenId);
      if (activeProjectId) fetchScreens(activeProjectId);
      if (selectedScreen?.id === screenId) setSelectedScreen(null);
    } catch {
      // silent
    } finally {
      setDeleting(null);
    }
  };

  const openHtml = (html: string) => {
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 size={24} className="animate-spin text-slate-400" />
      </div>
    );
  }

  // Detail view
  if (selectedScreen) {
    return (
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto">
          <button
            onClick={() => setSelectedScreen(null)}
            className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 mb-4"
          >
            <X size={14} /> Back to gallery
          </button>

          <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
            {selectedScreen.title || "Untitled Screen"}
          </h2>

          <div className="flex flex-wrap gap-2 mb-4">
            <span className={cn("px-2 py-0.5 text-xs rounded-full", STATUS_COLORS[selectedScreen.status] || "bg-slate-100 text-slate-600")}>
              {selectedScreen.status}
            </span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              {selectedScreen.device_type}
            </span>
            {selectedScreen.model_used && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                {selectedScreen.model_used}
              </span>
            )}
          </div>

          {selectedScreen.prompt && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Prompt</h4>
              <p className="text-sm text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
                {selectedScreen.prompt}
              </p>
            </div>
          )}

          {selectedScreen.source_findings && selectedScreen.source_findings.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Source Findings</h4>
              <div className="flex flex-wrap gap-1">
                {selectedScreen.source_findings.map((id: string) => (
                  <span key={id} className="px-2 py-0.5 text-xs bg-istara-100 dark:bg-istara-900/30 text-istara-700 dark:text-istara-400 rounded-full">
                    {id.slice(0, 8)}...
                  </span>
                ))}
              </div>
            </div>
          )}

          <p className="text-xs text-slate-400 mb-4">Created {formatDate(selectedScreen.created_at)}</p>

          <div className="flex gap-2 mb-6">
            {selectedScreen.html_content && (
              <button
                onClick={() => openHtml(selectedScreen.html_content)}
                className="flex items-center gap-1.5 px-3 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors"
              >
                <ExternalLink size={14} /> View HTML
              </button>
            )}
            <button
              onClick={() => handleDelete(selectedScreen.id)}
              disabled={deleting === selectedScreen.id}
              className="flex items-center gap-1.5 px-3 py-2 text-sm text-red-600 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            >
              <Trash2 size={14} /> Delete
            </button>
          </div>

          {selectedScreen.html_content && (
            <ScreenPreview html={selectedScreen.html_content} deviceType={selectedScreen.device_type} />
          )}
        </div>
      </div>
    );
  }

  // Gallery view
  return (
    <div className="flex-1 overflow-y-auto p-6">
      {screens.length === 0 ? (
        <div className="flex items-center justify-center h-full text-slate-400">
          <div className="text-center max-w-md">
            <LayoutGrid size={40} className="mx-auto mb-4 text-slate-300 dark:text-slate-600" />
            <p className="text-lg mb-2">No screens generated yet</p>
            <p className="text-sm">
              Try the Generate tab to create your first screen from research findings.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {screens.map((screen: any) => {
            const DeviceIcon = DEVICE_ICONS[screen.device_type] || Globe;
            return (
              <button
                key={screen.id}
                onClick={() => setSelectedScreen(screen)}
                className="text-left bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 hover:shadow-md hover:border-istara-300 dark:hover:border-istara-700 transition-all"
              >
                {/* Preview placeholder */}
                <div className="h-32 rounded-lg mb-3 flex items-center justify-center bg-gradient-to-br from-istara-50 to-violet-50 dark:from-istara-900/20 dark:to-violet-900/20 border border-slate-100 dark:border-slate-700">
                  <DeviceIcon size={32} className="text-slate-300 dark:text-slate-600" />
                </div>

                <h3 className="font-medium text-sm text-slate-900 dark:text-white truncate mb-1">
                  {screen.title || "Untitled Screen"}
                </h3>

                <div className="flex items-center gap-2 mb-2">
                  <span className="px-1.5 py-0.5 text-[10px] rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">
                    {screen.device_type}
                  </span>
                  <span className={cn("px-1.5 py-0.5 text-[10px] rounded", STATUS_COLORS[screen.status] || "bg-slate-100 text-slate-600")}>
                    {screen.status}
                  </span>
                </div>

                <p className="text-xs text-slate-400">
                  {formatDate(screen.created_at)}
                </p>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
