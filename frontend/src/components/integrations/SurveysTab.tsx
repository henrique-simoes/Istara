"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, FileQuestion, Trash2, Link2, ListChecks } from "lucide-react";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { useProjectStore } from "@/stores/projectStore";
import { permissionRequests, surveys as surveysApi } from "@/lib/api";
import { useRoleCapabilities } from "@/hooks/useRoleCapabilities";
import { cn } from "@/lib/utils";
import SurveySetupWizard from "./SurveySetupWizard";
import QuestionnaireStudio from "./QuestionnaireStudio";
import LinkedSurveysTable from "./LinkedSurveysTable";
import type { SurveyLink } from "@/lib/types";

const PLATFORM_META: Record<string, { label: string; color: string; bg: string }> = {
  surveymonkey: { label: "Survey Platform", color: "text-[#00BF6F]", bg: "bg-[#00BF6F]/10" },
  google_forms: { label: "Web Form", color: "text-[#673AB7]", bg: "bg-[#673AB7]/10" },
  typeform: { label: "Questionnaire Service", color: "text-[#262627]", bg: "bg-slate-100 dark:bg-slate-800" },
};

export default function SurveysTab() {
  const { surveyIntegrations, surveyLoading, fetchSurveyIntegrations } = useIntegrationsStore();
  const { activeProjectId } = useProjectStore();
  const { canManageProjectIntegrations: canManageSurveyIntegrations } = useRoleCapabilities();
  const [showWizard, setShowWizard] = useState(false);
  const [linkedSurveys, setLinkedSurveys] = useState<SurveyLink[]>([]);
  const [linksLoading, setLinksLoading] = useState(false);
  const [syncing, setSyncing] = useState<string | null>(null);

  // Studio state
  const [surveyTabMode, setSurveyTabMode] = useState<"platforms" | "studio">("platforms");
  const [linkNotice, setLinkNotice] = useState<string | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const fetchLinks = useCallback(async () => {
    setLinkedSurveys([]);
    setLinksLoading(true);
    if (!activeProjectId) {
      setLinkedSurveys([]);
      setLinksLoading(false);
      return;
    }
    try {
      const links = await surveysApi.links.list(activeProjectId);
      setLinkedSurveys(links.filter((link) => link.project_id === activeProjectId));
    } catch {
      // silent
    } finally {
      setLinksLoading(false);
    }
  }, [activeProjectId]);

  useEffect(() => {
    fetchSurveyIntegrations(activeProjectId);
    fetchLinks();
  }, [activeProjectId, fetchSurveyIntegrations, fetchLinks]);

  const scopedSurveyIntegrations = activeProjectId
    ? surveyIntegrations.filter((integration) => integration.project_id === activeProjectId)
    : [];

  const handleSync = async (linkId: string) => {
    if (!activeProjectId) return;
    setSyncing(linkId);
    setLinkError(null);
    setLinkNotice(null);
    try {
      const result = await surveysApi.links.sync(linkId, activeProjectId);
      if (result?.demo) {
        setLinkNotice("Demo survey: there are no platform responses to pull.");
      } else if (result?.status === "no_new_responses") {
        setLinkNotice("No responses on the platform yet.");
      } else {
        const fresh = result?.nuggets_created ?? 0;
        const already = result?.duplicate_answers_skipped ?? 0;
        setLinkNotice(
          `Stored ${fresh} new answer${fresh === 1 ? "" : "s"}` +
            (already ? `; ${already} already stored were skipped.` : ".")
        );
      }
      await fetchLinks();
    } catch (err) {
      setLinkError(err instanceof Error ? `Sync failed: ${err.message}` : "Sync failed.");
    } finally {
      setSyncing(null);
    }
  };

  const handleExportLink = async (linkId: string) => {
    if (!activeProjectId) return;
    setLinkError(null);
    setLinkNotice(null);
    try {
      const name = await surveysApi.links.exportCsv(linkId, activeProjectId);
      setLinkNotice(`Downloaded ${name}.`);
    } catch (err) {
      setLinkError(err instanceof Error ? `Export failed: ${err.message}` : "Export failed.");
    }
  };

  const handleDeleteIntegration = async (id: string) => {
    if (!activeProjectId) return;
    try {
      if (canManageSurveyIntegrations) {
        await surveysApi.integrations.delete(id, activeProjectId);
      } else {
        await permissionRequests.create({
          project_id: activeProjectId,
          action: "surveys.integration.delete",
          title: "Remove survey integration",
          details: "Request permission to remove a survey platform integration.",
          payload_summary: `Integration id: ${id}`,
        });
      }
      await fetchSurveyIntegrations(activeProjectId);
    } catch {
      // silent
    }
  };

  const handleConnectPlatform = async () => {
    if (canManageSurveyIntegrations) {
      setShowWizard(true);
      return;
    }
    if (!activeProjectId) return;
    await permissionRequests.create({
      project_id: activeProjectId,
      action: "surveys.integration.create",
      title: "Connect survey platform",
      details: "Request permission to connect an external survey platform for this project.",
    });
  };

  if (showWizard) {
    return (
      <SurveySetupWizard
        onClose={() => {
          setShowWizard(false);
          fetchSurveyIntegrations(activeProjectId);
        }}
      />
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Survey Platforms</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Connect external survey tools to import response data.
          </p>
        </div>
        <button
          onClick={handleConnectPlatform}
          disabled={!activeProjectId}
          className="flex items-center gap-1.5 px-3 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 dark:disabled:bg-slate-800 dark:disabled:text-slate-500 transition-colors"
        >
          <Plus size={14} />
          {canManageSurveyIntegrations ? "Connect Platform" : "Request Platform"}
        </button>
      </div>

      {/* Subtab Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        <button
          onClick={() => setSurveyTabMode("platforms")}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
            surveyTabMode === "platforms"
              ? "bg-istara-50 text-istara-700 dark:bg-istara-950/50 dark:text-istara-300"
              : "text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
          )}
        >
          <Link2 size={13} />
          Connected Platforms & Sync ({scopedSurveyIntegrations.length})
        </button>
        <button
          onClick={() => setSurveyTabMode("studio")}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
            surveyTabMode === "studio"
              ? "bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300"
              : "text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
          )}
        >
          <ListChecks size={13} className="text-purple-500" />
          Questionnaire Studio
        </button>
      </div>

      {surveyTabMode === "studio" ? (
        <QuestionnaireStudio projectId={activeProjectId} onRecorded={fetchLinks} />
      ) : (
        /* Connected Platforms Mode */
        <>
          {/* Integration cards */}
          {surveyLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-32 rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse" />
              ))}
            </div>
          ) : scopedSurveyIntegrations.length === 0 ? (
            <div className="text-center py-12 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
              <FileQuestion size={40} className="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">No external survey platforms connected</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
                Connect an external platform or use Questionnaire Studio to collect and ingest responses into the Research Spine.
              </p>
              <button
                onClick={handleConnectPlatform}
                disabled={!activeProjectId}
                className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 dark:disabled:bg-slate-800 dark:disabled:text-slate-500 transition-colors"
              >
                {canManageSurveyIntegrations ? "Connect First Platform" : "Request Platform Access"}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {scopedSurveyIntegrations.map((integration) => {
                const meta = PLATFORM_META[integration.platform] || { label: integration.platform, color: "text-slate-500", bg: "bg-slate-100" };
                return (
                  <div
                    key={integration.id}
                    className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full", meta.bg, meta.color)}>
                        {meta.label}
                      </span>
                      <button
                        onClick={() => handleDeleteIntegration(integration.id)}
                        aria-label="Remove integration"
                        className="p-1 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-1">{integration.name}</h3>
                    <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                      <span className={cn("w-2 h-2 rounded-full", integration.is_active ? "bg-green-500" : "bg-slate-300")} />
                      {integration.is_active ? "Connected" : "Disconnected"}
                    </div>
                    {integration.last_sync_at && (
                      <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                        Last sync: {new Date(integration.last_sync_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* Linked Surveys: platform links and surveys recorded in the Questionnaire Studio */}
      {(scopedSurveyIntegrations.length > 0 || linkedSurveys.length > 0) && (
        <LinkedSurveysTable
          links={linkedSurveys}
          loading={linksLoading}
          syncingId={syncing}
          notice={linkNotice}
          error={linkError}
          onSync={handleSync}
          onExport={handleExportLink}
        />
      )}
    </div>
  );
}
