"use client";

import { useEffect, useState } from "react";
import { FileOutput, Loader2, ChevronDown, ChevronRight, FileText } from "lucide-react";
import { interfaces as interfacesApi } from "@/lib/api";
import { useInterfacesStore } from "@/stores/interfacesStore";
import { useProjectStore } from "@/stores/projectStore";
import { cn, formatDate } from "@/lib/utils";

export default function HandoffTab() {
  const { screens, briefs, fetchScreens, fetchBriefs } = useInterfacesStore();
  const { activeProjectId } = useProjectStore();

  // Brief state
  const [generatingBrief, setGeneratingBrief] = useState(false);
  const [briefError, setBriefError] = useState<string | null>(null);
  const [expandedBriefId, setExpandedBriefId] = useState<string | null>(null);

  // Dev spec state
  const [selectedScreenId, setSelectedScreenId] = useState("");
  const [generatingSpec, setGeneratingSpec] = useState(false);
  const [devSpec, setDevSpec] = useState<any>(null);
  const [specError, setSpecError] = useState<string | null>(null);

  useEffect(() => {
    if (activeProjectId) {
      fetchBriefs(activeProjectId);
      fetchScreens(activeProjectId);
    }
  }, [activeProjectId, fetchBriefs, fetchScreens]);

  const handleGenerateBrief = async () => {
    if (!activeProjectId || generatingBrief) return;
    setGeneratingBrief(true);
    setBriefError(null);
    try {
      await interfacesApi.handoff.generateBrief({ project_id: activeProjectId });
      fetchBriefs(activeProjectId);
    } catch (e: any) {
      setBriefError(e.message);
    } finally {
      setGeneratingBrief(false);
    }
  };

  const handleGenerateSpec = async () => {
    if (!selectedScreenId || generatingSpec) return;
    setGeneratingSpec(true);
    setSpecError(null);
    setDevSpec(null);
    try {
      const result = await interfacesApi.handoff.generateDevSpec({ screen_id: selectedScreenId });
      setDevSpec(result);
    } catch (e: any) {
      setSpecError(e.message);
    } finally {
      setGeneratingSpec(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-8">

        {/* Design Briefs */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Design Briefs</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Auto-generated summaries of design decisions and research findings.
              </p>
            </div>
            <button
              onClick={handleGenerateBrief}
              disabled={generatingBrief}
              className="flex items-center gap-1.5 px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {generatingBrief ? <Loader2 size={14} className="animate-spin" /> : <FileOutput size={14} />}
              Generate Brief
            </button>
          </div>

          {briefError && (
            <div className="rounded-lg px-4 py-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm mb-4">
              {briefError}
            </div>
          )}

          {briefs.length === 0 ? (
            <div className="text-center py-8 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
              <FileText size={32} className="mx-auto mb-2 text-slate-300 dark:text-slate-600" />
              <p className="text-sm text-slate-400">No design briefs yet. Generate one to summarize your design decisions.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {briefs.map((brief: any) => (
                <div
                  key={brief.id}
                  className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden"
                >
                  <button
                    onClick={() => setExpandedBriefId(expandedBriefId === brief.id ? null : brief.id)}
                    className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                  >
                    <div>
                      <h4 className="text-sm font-medium text-slate-900 dark:text-white">
                        {brief.title || "Untitled Brief"}
                      </h4>
                      <p className="text-xs text-slate-400 mt-0.5">{formatDate(brief.created_at)}</p>
                    </div>
                    {expandedBriefId === brief.id ? (
                      <ChevronDown size={16} className="text-slate-400 shrink-0" />
                    ) : (
                      <ChevronRight size={16} className="text-slate-400 shrink-0" />
                    )}
                  </button>
                  {expandedBriefId === brief.id && (
                    <div className="px-4 pb-4 border-t border-slate-100 dark:border-slate-800">
                      <div className="mt-3 text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                        {brief.content}
                      </div>

                      {/* UX Laws Referenced */}
                      {brief.ux_laws && brief.ux_laws.length > 0 && (
                        <div className="mt-4 p-3 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800">
                          <h5 className="text-xs font-semibold text-indigo-700 dark:text-indigo-400 mb-2">UX Laws Referenced</h5>
                          <div className="flex flex-wrap gap-1.5">
                            {brief.ux_laws.map((law: string, i: number) => (
                              <span key={i} className="inline-flex px-2 py-0.5 text-xs rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">
                                {law}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Evidence / Source Findings */}
                      {brief.source_findings && brief.source_findings.length > 0 && (
                        <div className="mt-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
                          <h5 className="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2">
                            Evidence ({brief.source_findings.length} finding{brief.source_findings.length !== 1 ? "s" : ""})
                          </h5>
                          <div className="space-y-1.5">
                            {brief.source_findings.slice(0, 5).map((f: any, i: number) => (
                              <div key={i} className="flex items-start gap-2 text-xs">
                                <span className={`shrink-0 px-1.5 py-0.5 rounded font-medium ${
                                  f.type === "nugget" ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" :
                                  f.type === "insight" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" :
                                  "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
                                }`}>
                                  {f.type || "finding"}
                                </span>
                                <span className="text-slate-600 dark:text-slate-400 line-clamp-2">{f.text}</span>
                              </div>
                            ))}
                            {brief.source_findings.length > 5 && (
                              <p className="text-xs text-slate-400 italic">+{brief.source_findings.length - 5} more</p>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Recommendations with law references */}
                      {brief.recommendations && brief.recommendations.length > 0 && (
                        <div className="mt-3 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                          <h5 className="text-xs font-semibold text-green-700 dark:text-green-400 mb-2">Recommendations</h5>
                          <ul className="space-y-1.5 list-disc list-inside text-xs text-green-800 dark:text-green-300">
                            {brief.recommendations.map((rec: any, i: number) => (
                              <li key={i}>
                                {typeof rec === "string" ? rec : rec.text}
                                {rec.law && (
                                  <span className="ml-1 text-indigo-600 dark:text-indigo-400 font-medium">({rec.law})</span>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Dev Specs */}
        <section>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">Dev Specs</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
            Generate developer specifications from a screen design.
          </p>

          {screens.length === 0 ? (
            <div className="text-center py-8 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
              <FileText size={32} className="mx-auto mb-2 text-slate-300 dark:text-slate-600" />
              <p className="text-sm text-slate-400">No screens available. Generate screens first in the Generate tab.</p>
            </div>
          ) : (
            <>
              <div className="flex gap-2 mb-4">
                <select
                  value={selectedScreenId}
                  onChange={(e) => setSelectedScreenId(e.target.value)}
                  className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                >
                  <option value="">Select a screen...</option>
                  {screens.map((screen: any) => (
                    <option key={screen.id} value={screen.id}>
                      {screen.title || screen.id.slice(0, 8)} ({screen.device_type})
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleGenerateSpec}
                  disabled={!selectedScreenId || generatingSpec}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {generatingSpec ? <Loader2 size={14} className="animate-spin" /> : <FileOutput size={14} />}
                  Generate Spec
                </button>
              </div>

              {specError && (
                <div className="rounded-lg px-4 py-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm mb-4">
                  {specError}
                </div>
              )}

              {devSpec && (
                <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                  <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Developer Specification</h4>
                  <div className="text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
                    {typeof devSpec === "string" ? devSpec : devSpec.content || JSON.stringify(devSpec, null, 2)}
                  </div>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
