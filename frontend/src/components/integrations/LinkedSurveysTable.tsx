"use client";

import { Download, Link2, RefreshCw, Search } from "lucide-react";
import type { SurveyLink } from "@/lib/types";

/** Surveys recorded in the Questionnaire Studio have no platform to pull from. */
export const LOCAL_STUDIO_INTEGRATION = "local_studio";

interface LinkedSurveysTableProps {
  links: SurveyLink[];
  loading: boolean;
  syncingId: string | null;
  notice: string | null;
  error: string | null;
  onSync: (linkId: string) => void;
  onExport: (linkId: string) => void;
  onAnalyse: (linkId: string) => void;
}

const HEAD = "px-5 py-2 text-xs font-medium text-slate-500 dark:text-slate-400";
const ICON_BUTTON =
  "p-1.5 rounded-lg text-slate-500 hover:text-istara-600 hover:bg-istara-50 dark:hover:bg-istara-900/20 transition-colors disabled:opacity-50";

function LinkRows({ links, syncingId, onSync, onExport, onAnalyse }: Omit<LinkedSurveysTableProps, "loading" | "notice" | "error">) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-100 dark:border-slate-800">
            <th className={`${HEAD} text-left`}>Survey Name</th>
            <th className={`${HEAD} text-left`}>Responses</th>
            <th className={`${HEAD} text-left`}>Last Response</th>
            <th className={`${HEAD} text-right`}>Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {links.map((link) => {
            const local = link.integration_id === LOCAL_STUDIO_INTEGRATION;
            return (
              <tr key={link.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                <td className="px-5 py-3 text-sm text-slate-900 dark:text-white">
                  {link.external_survey_name}
                  {local && <span className="ml-2 text-[11px] text-slate-500 dark:text-slate-400">recorded in the studio</span>}
                </td>
                <td className="px-5 py-3 text-sm text-slate-600 dark:text-slate-300">{link.response_count}</td>
                <td className="px-5 py-3 text-xs text-slate-500 dark:text-slate-400">
                  {link.last_response_at ? new Date(link.last_response_at).toLocaleDateString() : "---"}
                </td>
                <td className="px-5 py-3 text-right whitespace-nowrap">
                  <button
                    onClick={() => onAnalyse(link.id)}
                    aria-label={`Analyse ${link.external_survey_name} responses`}
                    title="Analyse the stored answers (creates a task)"
                    className={ICON_BUTTON}
                  >
                    <Search size={14} />
                  </button>
                  <button
                    onClick={() => onExport(link.id)}
                    aria-label={`Export ${link.external_survey_name} responses as CSV`}
                    title="Export stored answers (CSV)"
                    className={ICON_BUTTON}
                  >
                    <Download size={14} />
                  </button>
                  {!local && (
                    <button
                      onClick={() => onSync(link.id)}
                      disabled={syncingId === link.id}
                      aria-label={`Sync ${link.external_survey_name} responses`}
                      className={ICON_BUTTON}
                    >
                      <RefreshCw size={14} className={syncingId === link.id ? "animate-spin" : ""} />
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function LinkedSurveysTable(props: LinkedSurveysTableProps) {
  const { links, loading, notice, error } = props;
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-200 dark:border-slate-800">
        <Link2 size={16} className="text-slate-400" />
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Linked Surveys</h3>
      </div>
      {error && <p role="alert" className="px-5 pt-3 text-xs text-red-600 dark:text-red-400">{error}</p>}
      {notice && !error && <p role="status" className="px-5 pt-3 text-xs text-slate-600 dark:text-slate-300">{notice}</p>}
      {loading ? (
        <div className="p-4 space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="h-12 rounded-lg bg-slate-100 dark:bg-slate-800 animate-pulse" />
          ))}
        </div>
      ) : links.length === 0 ? (
        <div className="px-5 py-8 text-center">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No surveys linked yet. Surveys from connected platforms and the Questionnaire Studio appear here.
          </p>
        </div>
      ) : (
        <LinkRows {...props} />
      )}
    </div>
  );
}
