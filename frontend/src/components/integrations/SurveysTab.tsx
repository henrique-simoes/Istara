"use client";

import { useEffect, useState } from "react";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { useProjectStore } from "@/stores/projectStore";
import { permissionRequests, surveys as surveysApi } from "@/lib/api";
import { useRoleCapabilities } from "@/hooks/useRoleCapabilities";
import SurveySetupWizard from "./SurveySetupWizard";
import QuestionnaireStudio from "./QuestionnaireStudio";
import LinkedSurveysTable from "./LinkedSurveysTable";
import SurveyPlatformCards, { InlineStatus, SurveyModeTabs, SurveysHeader, type SurveyMode } from "./SurveyPlatformCards";
import { useLinkedSurveys } from "./useLinkedSurveys";


export default function SurveysTab() {
  const { surveyIntegrations, surveyLoading, fetchSurveyIntegrations } = useIntegrationsStore();
  const { activeProjectId } = useProjectStore();
  const { canManageProjectIntegrations: canManageSurveyIntegrations } = useRoleCapabilities();
  const [showWizard, setShowWizard] = useState(false);
  const [surveyTabMode, setSurveyTabMode] = useState<SurveyMode>("platforms");
  const linked = useLinkedSurveys(activeProjectId);
  const fetchLinks = linked.refresh;

  useEffect(() => {
    fetchSurveyIntegrations(activeProjectId);
    fetchLinks();
  }, [activeProjectId, fetchSurveyIntegrations, fetchLinks]);

  const scopedSurveyIntegrations = activeProjectId
    ? surveyIntegrations.filter((integration) => integration.project_id === activeProjectId)
    : [];

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
      if (!canManageSurveyIntegrations) linked.setNotice("Request sent to the project admins.");
    } catch (err) {
      linked.setError(err instanceof Error ? `Could not remove the platform: ${err.message}` : "Could not remove the platform.");
    }
  };

  const handleConnectPlatform = async () => {
    if (canManageSurveyIntegrations) {
      setShowWizard(true);
      return;
    }
    if (!activeProjectId) return;
    try {
      await permissionRequests.create({
        project_id: activeProjectId,
        action: "surveys.integration.create",
        title: "Connect survey platform",
        details: "Request permission to connect an external survey platform for this project.",
      });
      linked.setNotice("Request sent to the project admins.");
    } catch (err) {
      linked.setError(err instanceof Error ? `Could not send the request: ${err.message}` : "Could not send the request.");
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
      <SurveysHeader canManage={canManageSurveyIntegrations} disabled={!activeProjectId} onConnect={handleConnectPlatform} />

      <SurveyModeTabs mode={surveyTabMode} platformCount={scopedSurveyIntegrations.length} onChange={setSurveyTabMode} />

      {surveyTabMode === "studio" ? (
        <QuestionnaireStudio projectId={activeProjectId} onRecorded={fetchLinks} />
      ) : (
        <SurveyPlatformCards
          loading={surveyLoading}
          integrations={scopedSurveyIntegrations}
          canManage={canManageSurveyIntegrations}
          projectId={activeProjectId}
          onConnect={handleConnectPlatform}
          onRemove={handleDeleteIntegration}
        />
      )}

      {/* Linked Surveys: platform links and surveys recorded in the Questionnaire Studio */}
      {(scopedSurveyIntegrations.length > 0 || linked.links.length > 0) ? (
        <LinkedSurveysTable
          links={linked.links}
          loading={linked.loading}
          syncingId={linked.syncingId}
          notice={linked.notice}
          error={linked.error}
          onSync={linked.sync}
          onExport={linked.exportLink}
          onAnalyse={linked.analyse}
        />
      ) : (
        <InlineStatus notice={linked.notice} error={linked.error} />
      )}
    </div>
  );
}
