"use client";

import { useCallback, useState } from "react";
import { surveys as surveysApi } from "@/lib/api";
import type { SurveyLink } from "@/lib/types";

function describeSync(result: { demo?: boolean; status?: string; nuggets_created?: number; duplicate_answers_skipped?: number }): string {
  if (result?.demo) return "Demo survey: there are no platform responses to pull.";
  if (result?.status === "no_new_responses") return "No responses on the platform yet.";
  const fresh = result?.nuggets_created ?? 0;
  const already = result?.duplicate_answers_skipped ?? 0;
  return `Stored ${fresh} new answer${fresh === 1 ? "" : "s"}` + (already ? `; ${already} already stored were skipped.` : ".");
}

function failure(prefix: string, err: unknown): string {
  return err instanceof Error ? `${prefix}: ${err.message}` : `${prefix}.`;
}

/** Linked surveys for the active project: list, sync (idempotent server-side) and CSV export. */
export function useLinkedSurveys(projectId: string | null) {
  const [links, setLinks] = useState<SurveyLink[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLinks([]);
    if (!projectId) return;
    setLoading(true);
    try {
      const all = await surveysApi.links.list(projectId);
      setLinks(all.filter((link) => link.project_id === projectId));
    } catch (err) {
      setError(failure("Could not load linked surveys", err));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const sync = async (linkId: string) => {
    if (!projectId) return;
    setSyncingId(linkId);
    setError(null);
    setNotice(null);
    try {
      setNotice(describeSync(await surveysApi.links.sync(linkId, projectId)));
      await refresh();
    } catch (err) {
      setError(failure("Sync failed", err));
    } finally {
      setSyncingId(null);
    }
  };

  const exportLink = async (linkId: string) => {
    if (!projectId) return;
    setError(null);
    setNotice(null);
    try {
      setNotice(`Downloaded ${await surveysApi.links.exportCsv(linkId, projectId)}.`);
    } catch (err) {
      setError(failure("Export failed", err));
    }
  };

  const analyse = async (linkId: string) => {
    if (!projectId) return;
    setError(null);
    setNotice(null);
    try {
      const result = await surveysApi.links.analyse(linkId, projectId);
      setNotice(
        `Created an analysis task for ${result.answers} answer${result.answers === 1 ? "" : "s"} on the Tasks board.`
      );
    } catch (err) {
      setError(failure("Could not start the analysis", err));
    }
  };

  return { links, loading, syncingId, notice, error, setNotice, setError, refresh, sync, exportLink, analyse };
}
