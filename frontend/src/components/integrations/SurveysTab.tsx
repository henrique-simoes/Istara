"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, FileQuestion, RefreshCw, Trash2, Link2, ListChecks, Sparkles, Send, CheckCircle2, Loader2, ClipboardList } from "lucide-react";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { useProjectStore } from "@/stores/projectStore";
import { permissionRequests, surveys as surveysApi } from "@/lib/api";
import { post } from "@/lib/apiClient";
import { useRoleCapabilities } from "@/hooks/useRoleCapabilities";
import { cn } from "@/lib/utils";
import SurveySetupWizard from "./SurveySetupWizard";
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
  const [surveyTitle, setSurveyTitle] = useState("Caregiver Experience & Workload Survey");
  const [questions, setQuestions] = useState<string[]>([
    "How satisfied are you with the medication notification schedule? (1 = Very Frustrated, 5 = Highly Satisfied)",
    "What was the most difficult step in sharing care updates with other family members?",
    "Which aspect of the clinical oversight dashboard would you improve first?",
  ]);
  const [newQuestionText, setNewQuestionText] = useState("");
  const [answers, setAnswers] = useState<Record<number, string>>({
    0: "2 - Notifications arrived at unpredictable times during work shifts, causing alert fatigue.",
    1: "Adding secondary caregivers required multiple manual authorization steps that timed out.",
    2: "Clearer visibility of clinical review status and audit logs on care plan changes.",
  });
  const [submittingResponse, setSubmittingResponse] = useState(false);
  const [ingestSuccess, setIngestSuccess] = useState<{
    nuggets: number;
    evidence_units: number;
  } | null>(null);
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
    try {
      await surveysApi.links.sync(linkId, activeProjectId);
      await fetchLinks();
    } catch {
      // silent
    } finally {
      setSyncing(null);
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

  const handleIngestDirectSurvey = async () => {
    if (!activeProjectId || submittingResponse) return;
    setSubmittingResponse(true);
    setIngestSuccess(null);
    try {
      const resp = await post<any>("/api/surveys/responses/ingest", {
        project_id: activeProjectId,
        survey_name: surveyTitle,
        responses: [
          {
            id: `resp-${Date.now()}`,
            answers: questions.map((q, idx) => ({
              question: q,
              answer: answers[idx] || "No response provided",
            })),
          },
        ],
      });
      setIngestSuccess({
        nuggets: resp.created || 0,
        evidence_units: resp.evidence_units_created || 0,
      });
      await fetchLinks();
    } catch (e) {
      console.error("Failed to ingest survey response:", e);
    } finally {
      setSubmittingResponse(false);
    }
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
          Questionnaire Studio & Research Spine Ingestion
        </button>
      </div>

      {surveyTabMode === "studio" ? (
        /* Questionnaire Studio & Research Spine Ingestion */
        <div className="space-y-6">
          {ingestSuccess && (
            <div className="flex items-center justify-between p-3.5 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 text-xs">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} />
                <span>
                  <strong>Success!</strong> Ingested {ingestSuccess.nuggets} provisional nuggets and {ingestSuccess.evidence_units} evidence units directly into the Research Spine.
                </span>
              </div>
              <button onClick={() => setIngestSuccess(null)} className="text-emerald-500 hover:text-emerald-700">×</button>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Survey Definition Card */}
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <ClipboardList size={16} className="text-purple-600 dark:text-purple-400" />
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Survey Definition</h3>
                </div>
                <span className="text-[11px] text-slate-400 font-mono">{questions.length} Questions</span>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500 block mb-1">Survey Title</label>
                <input
                  type="text"
                  value={surveyTitle}
                  onChange={(e) => setSurveyTitle(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-istara-500"
                />
              </div>

              <div className="space-y-2.5">
                <label className="text-xs font-semibold text-slate-500 block">Questions</label>
                {questions.map((q, idx) => (
                  <div key={idx} className="flex items-start gap-2 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/60 text-xs">
                    <span className="font-semibold text-purple-600 dark:text-purple-400 shrink-0">Q{idx + 1}:</span>
                    <span className="text-slate-800 dark:text-slate-200 flex-1">{q}</span>
                    {questions.length > 1 && (
                      <button
                        onClick={() => setQuestions(questions.filter((_, i) => i !== idx))}
                        className="text-slate-400 hover:text-red-500 transition-colors"
                        title="Remove question"
                      >
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                ))}

                <div className="flex items-center gap-2 pt-2">
                  <input
                    type="text"
                    placeholder="Add a new survey question..."
                    value={newQuestionText}
                    onChange={(e) => setNewQuestionText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && newQuestionText.trim()) {
                        setQuestions([...questions, newQuestionText.trim()]);
                        setNewQuestionText("");
                      }
                    }}
                    className="flex-1 px-3 py-1.5 text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-istara-500"
                  />
                  <button
                    onClick={() => {
                      if (newQuestionText.trim()) {
                        setQuestions([...questions, newQuestionText.trim()]);
                        setNewQuestionText("");
                      }
                    }}
                    className="px-3 py-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg transition-colors shrink-0"
                  >
                    Add Q
                  </button>
                </div>
              </div>
            </div>

            {/* Interactive Participant Simulation & Spine Ingestion Form */}
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4 shadow-xs">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles size={16} className="text-blue-600 dark:text-blue-400" />
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Simulate Participant Response</h3>
                </div>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 font-medium">
                  Live Spine Input
                </span>
              </div>

              <div className="space-y-3">
                {questions.map((q, idx) => (
                  <div key={idx} className="space-y-1">
                    <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                      Q{idx + 1}: {q}
                    </p>
                    <textarea
                      rows={2}
                      value={answers[idx] || ""}
                      onChange={(e) => setAnswers({ ...answers, [idx]: e.target.value })}
                      placeholder="Participant answer..."
                      className="w-full px-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-istara-500 font-sans"
                    />
                  </div>
                ))}
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end">
                <button
                  onClick={handleIngestDirectSurvey}
                  disabled={submittingResponse || !activeProjectId}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg bg-istara-600 hover:bg-istara-700 text-white transition-colors disabled:opacity-50 shadow-xs"
                >
                  {submittingResponse ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                  Submit & Ingest into Research Spine
                </button>
              </div>
            </div>
          </div>
        </div>
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

      {/* Linked Surveys table */}
      {scopedSurveyIntegrations.length > 0 && (
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
