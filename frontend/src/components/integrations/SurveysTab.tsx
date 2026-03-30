"use client";

import { useEffect, useState } from "react";
import { Plus, FileQuestion, ExternalLink, RefreshCw, Trash2, Link2 } from "lucide-react";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { surveys as surveysApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import SurveySetupWizard from "./SurveySetupWizard";
import type { SurveyLink } from "@/lib/types";

const PLATFORM_META: Record<string, { label: string; color: string; bg: string }> = {
  surveymonkey: { label: "SurveyMonkey", color: "text-[#00BF6F]", bg: "bg-[#00BF6F]/10" },
  google_forms: { label: "Google Forms", color: "text-[#673AB7]", bg: "bg-[#673AB7]/10" },
  typeform: { label: "Typeform", color: "text-[#262627]", bg: "bg-slate-100 dark:bg-slate-800" },
};

export default function SurveysTab() {
  const { surveyIntegrations, surveyLoading, fetchSurveyIntegrations } = useIntegrationsStore();
  const [showWizard, setShowWizard] = useState(false);
  const [linkedSurveys, setLinkedSurveys] = useState<SurveyLink[]>([]);
  const [linksLoading, setLinksLoading] = useState(false);
  const [syncing, setSyncing] = useState<string | null>(null);

  useEffect(() => {
    fetchSurveyIntegrations();
    fetchLinks();
  }, [fetchSurveyIntegrations]);

  const fetchLinks = async () => {
    setLinksLoading(true);
    try {
      const links = await surveysApi.links.list();
      setLinkedSurveys(links);
    } catch {
      // silent
    } finally {
      setLinksLoading(false);
    }
  };

  const handleSync = async (linkId: string) => {
    setSyncing(linkId);
    try {
      await surveysApi.links.sync(linkId);
      await fetchLinks();
    } catch {
      // silent
    } finally {
      setSyncing(null);
    }
  };

  const handleDeleteIntegration = async (id: string) => {
    try {
      await surveysApi.integrations.delete(id);
      await fetchSurveyIntegrations();
    } catch {
      // silent
    }
  };

  if (showWizard) {
    return (
      <SurveySetupWizard
        onClose={() => {
          setShowWizard(false);
          fetchSurveyIntegrations();
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
          onClick={() => setShowWizard(true)}
          className="flex items-center gap-1.5 px-3 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors"
        >
          <Plus size={14} />
          Connect Platform
        </button>
      </div>

      {/* Integration cards */}
      {surveyLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse" />
          ))}
        </div>
      ) : surveyIntegrations.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
          <FileQuestion size={40} className="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">No survey platforms connected</p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
            Connect SurveyMonkey, Google Forms, or Typeform to pull in survey responses.
          </p>
          <button
            onClick={() => setShowWizard(true)}
            className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors"
          >
            Connect First Platform
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {surveyIntegrations.map((integration) => {
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

      {/* Linked Surveys table */}
      {surveyIntegrations.length > 0 && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <Link2 size={16} className="text-slate-400" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Linked Surveys</h3>
            </div>
          </div>

          {linksLoading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="h-12 rounded-lg bg-slate-100 dark:bg-slate-800 animate-pulse" />
              ))}
            </div>
          ) : linkedSurveys.length === 0 ? (
            <div className="px-5 py-8 text-center">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                No surveys linked yet. Surveys from connected platforms will appear here.
              </p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800">
                  <th className="px-5 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">Survey Name</th>
                  <th className="px-5 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">Responses</th>
                  <th className="px-5 py-2 text-left text-xs font-medium text-slate-500 dark:text-slate-400">Last Response</th>
                  <th className="px-5 py-2 text-right text-xs font-medium text-slate-500 dark:text-slate-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {linkedSurveys.map((link) => (
                  <tr key={link.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-5 py-3 text-sm text-slate-900 dark:text-white">{link.external_survey_name}</td>
                    <td className="px-5 py-3 text-sm text-slate-600 dark:text-slate-300">{link.response_count}</td>
                    <td className="px-5 py-3 text-xs text-slate-500 dark:text-slate-400">
                      {link.last_response_at ? new Date(link.last_response_at).toLocaleDateString() : "---"}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={() => handleSync(link.id)}
                        disabled={syncing === link.id}
                        aria-label="Sync survey responses"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-istara-600 hover:bg-istara-50 dark:hover:bg-istara-900/20 transition-colors disabled:opacity-50"
                      >
                        <RefreshCw size={14} className={syncing === link.id ? "animate-spin" : ""} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
