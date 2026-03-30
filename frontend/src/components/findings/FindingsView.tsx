"use client";

import { useEffect, useState, lazy, Suspense } from "react";
import {
  Diamond,
  ChevronDown,
  ChevronRight,
  FileText,
  Lightbulb,
  Target,
  Sparkles,
  Link2,
  BookOpen,
  ClipboardCheck,
  Layers,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { findings as findingsApi } from "@/lib/api";
import type { FindingsSummary, Nugget, Fact, Insight, Recommendation, ProjectPhase } from "@/lib/types";
import { cn, confidenceColor, phaseLabel } from "@/lib/utils";
import AtomicDrilldown from "./AtomicDrilldown";
import LawBadge from "@/components/laws/LawBadge";
import ViewOnboarding from "@/components/common/ViewOnboarding";

// Research Integrity sub-views
const CodebookViewer = lazy(() => import("./CodebookViewer"));
const CodeReviewQueue = lazy(() => import("./CodeReviewQueue"));
const ProjectReportsView = lazy(() => import("./ProjectReportsView"));

type FindingsTab = "evidence" | "codebook" | "review" | "reports";

const FINDINGS_TABS: { id: FindingsTab; label: string; icon: typeof Diamond }[] = [
  { id: "evidence", label: "Evidence", icon: Sparkles },
  { id: "codebook", label: "Codebook", icon: BookOpen },
  { id: "review", label: "Review", icon: ClipboardCheck },
  { id: "reports", label: "Reports", icon: Layers },
];

const PHASE_TABS: { id: ProjectPhase; label: string; icon: typeof Diamond }[] = [
  { id: "discover", label: "Discover", icon: Diamond },
  { id: "define", label: "Define", icon: Diamond },
  { id: "develop", label: "Develop", icon: Diamond },
  { id: "deliver", label: "Deliver", icon: Diamond },
];

export default function FindingsView() {
  const { activeProjectId } = useProjectStore();
  const [activeTab, setActiveTab] = useState<FindingsTab>("evidence");
  const [activePhase, setActivePhase] = useState<ProjectPhase>("discover");
  const [summary, setSummary] = useState<FindingsSummary | null>(null);
  const [nuggets, setNuggets] = useState<Nugget[]>([]);
  const [facts, setFacts] = useState<Fact[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [expandedSection, setExpandedSection] = useState<string | null>("insights");
  const [drilldownFinding, setDrilldownFinding] = useState<{
    id: string;
    type: "recommendation" | "insight" | "fact" | "nugget";
    text: string;
  } | null>(null);

  useEffect(() => {
    if (!activeProjectId) return;

    findingsApi.summary(activeProjectId).then(setSummary).catch(console.error);
    findingsApi.nuggets(activeProjectId).then(setNuggets).catch(console.error);
    findingsApi.facts(activeProjectId).then(setFacts).catch(console.error);
    findingsApi.insights(activeProjectId).then(setInsights).catch(console.error);
    findingsApi.recommendations(activeProjectId).then(setRecommendations).catch(console.error);
  }, [activeProjectId]);

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <p>Select a project to see findings.</p>
      </div>
    );
  }

  const phaseNuggets = nuggets.filter((n) => n.phase === activePhase);
  const phaseFacts = facts.filter((f) => f.phase === activePhase);
  const phaseInsights = insights.filter((i) => i.phase === activePhase);
  const phaseRecs = recommendations.filter((r) => r.phase === activePhase);
  const phaseStats = summary?.by_phase[activePhase];

  /** Count evidence links for a finding based on its type */
  const getEvidenceLinkCount = (item: any, sectionId: string): number => {
    const parseIds = (raw: string | string[] | undefined | null): string[] => {
      if (!raw) return [];
      if (Array.isArray(raw)) return raw;
      try { return JSON.parse(raw); } catch { return []; }
    };
    switch (sectionId) {
      case "insights":
        return parseIds(item.fact_ids).length;
      case "facts":
        return parseIds(item.nugget_ids).length;
      case "recommendations":
        return parseIds(item.insight_ids).length;
      default:
        return 0; // nuggets are leaf nodes
    }
  };

  const sections = [
    {
      id: "insights",
      label: "Insights",
      icon: Lightbulb,
      count: phaseInsights.length,
      color: "text-yellow-600",
      items: phaseInsights,
    },
    {
      id: "recommendations",
      label: "Recommendations",
      icon: Target,
      count: phaseRecs.length,
      color: "text-green-600",
      items: phaseRecs,
    },
    {
      id: "facts",
      label: "Facts",
      icon: FileText,
      count: phaseFacts.length,
      color: "text-blue-600",
      items: phaseFacts,
    },
    {
      id: "nuggets",
      label: "Nuggets",
      icon: Sparkles,
      count: phaseNuggets.length,
      color: "text-purple-600",
      items: phaseNuggets,
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto">
      <ViewOnboarding viewId="findings" title="Research Evidence" description="Nuggets, facts, insights, and recommendations from your research. Auto-generated as agents analyze data. Filter by phase and type." chatPrompt="How do findings work in Istara?" />
      {/* Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
          🔍 Findings
        </h2>

        {/* Top-level tabs: Evidence | Codebook | Review | Reports */}
        <div
          className="flex gap-1 mb-3 border-b border-slate-200 dark:border-slate-700"
          role="tablist"
          aria-label="Findings views"
        >
          {FINDINGS_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              role="tab"
              aria-selected={activeTab === tab.id}
              className={cn(
                "flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors -mb-px",
                activeTab === tab.id
                  ? "border-istara-600 text-istara-600 dark:border-istara-400 dark:text-istara-400"
                  : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
              )}
            >
              <tab.icon size={14} />
              {tab.label}
            </button>
          ))}
        </div>

      </div>

      {/* Research Integrity sub-views */}
      {activeTab === "codebook" && activeProjectId && (
        <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading codebook...</div>}>
          <CodebookViewer projectId={activeProjectId} />
        </Suspense>
      )}
      {activeTab === "review" && activeProjectId && (
        <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading review queue...</div>}>
          <CodeReviewQueue projectId={activeProjectId} />
        </Suspense>
      )}
      {activeTab === "reports" && activeProjectId && (
        <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading reports...</div>}>
          <ProjectReportsView projectId={activeProjectId} />
        </Suspense>
      )}

      {/* Evidence tab content */}
      {activeTab === "evidence" && (
      <>
      <div className="p-4 border-b border-slate-200 dark:border-slate-800">
        {/* Phase tabs */}
        <div
          className="flex gap-1 bg-slate-100 dark:bg-slate-800 rounded-lg p-1"
          role="tablist"
          aria-label="Double Diamond phases"
          onKeyDown={(e) => {
            const phases: ProjectPhase[] = ["discover", "define", "develop", "deliver"];
            const idx = phases.indexOf(activePhase);
            if (e.key === "ArrowRight" && idx < phases.length - 1) {
              e.preventDefault();
              setActivePhase(phases[idx + 1]);
            }
            if (e.key === "ArrowLeft" && idx > 0) {
              e.preventDefault();
              setActivePhase(phases[idx - 1]);
            }
          }}
        >
          {PHASE_TABS.map((tab) => {
            const tabStats = summary?.by_phase[tab.id];
            const tabTotal = tabStats
              ? (tabStats.nuggets || 0) + (tabStats.facts || 0) + (tabStats.insights || 0) + (tabStats.recommendations || 0)
              : 0;
            return (
              <button
                key={tab.id}
                onClick={() => setActivePhase(tab.id)}
                role="tab"
                aria-selected={activePhase === tab.id}
                tabIndex={activePhase === tab.id ? 0 : -1}
                className={cn(
                  "flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors",
                  activePhase === tab.id
                    ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm"
                    : "text-slate-500 dark:text-slate-400 hover:text-slate-700"
                )}
              >
                💎 {tab.label}
                {summary && (
                  <span className="ml-1.5 text-xs text-slate-400">
                    ({tabTotal})
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Summary stats */}
      {summary && (
        <div className="grid grid-cols-4 gap-3 p-4">
          {[
            { label: "Nuggets", value: summary.totals.nuggets, emoji: "✨" },
            { label: "Facts", value: summary.totals.facts, emoji: "📄" },
            { label: "Insights", value: summary.totals.insights, emoji: "💡" },
            { label: "Recommendations", value: summary.totals.recommendations, emoji: "🎯" },
          ].map((stat) => (
            <div
              key={stat.label}
              className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3 text-center"
            >
              <span className="text-xl">{stat.emoji}</span>
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{stat.value}</p>
              <p className="text-xs text-slate-500">{stat.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Sections */}
      <div className="p-4 space-y-3">
        {sections.map((section) => (
          <div
            key={section.id}
            className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden"
          >
            {/* Section header */}
            <button
              onClick={() =>
                setExpandedSection(expandedSection === section.id ? null : section.id)
              }
              className="flex items-center justify-between w-full p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                {expandedSection === section.id ? (
                  <ChevronDown size={16} className="text-slate-400" />
                ) : (
                  <ChevronRight size={16} className="text-slate-400" />
                )}
                <section.icon size={16} className={section.color} />
                <span className="font-medium text-sm text-slate-900 dark:text-white">
                  {section.label}
                </span>
                <span className="text-xs bg-slate-200 dark:bg-slate-700 px-1.5 py-0.5 rounded-full text-slate-500">
                  {section.count}
                </span>
              </div>
            </button>

            {/* Section content */}
            {expandedSection === section.id && (
              <div className="border-t border-slate-200 dark:border-slate-700 divide-y divide-slate-100 dark:divide-slate-800">
                {section.items.length === 0 ? (
                  <p className="p-4 text-sm text-slate-400 text-center">
                    No {section.label.toLowerCase()} yet for this phase.
                  </p>
                ) : (
                  section.items.map((item: any) => {
                    const linkCount = getEvidenceLinkCount(item, section.id);
                    return (
                      <div
                        key={item.id}
                        onClick={() =>
                          setDrilldownFinding({
                            id: item.id,
                            type: section.id as any,
                            text: item.text,
                          })
                        }
                        className="p-3 hover:bg-slate-50 dark:hover:bg-slate-800/30 cursor-pointer">
                        <div className="flex items-start gap-2">
                          <p className="flex-1 text-sm text-slate-900 dark:text-white">{item.text}</p>
                          {linkCount > 0 && (
                            <span
                              className="shrink-0 inline-flex items-center gap-0.5 text-[10px] font-medium text-istara-600 dark:text-istara-400 bg-istara-50 dark:bg-istara-900/20 rounded-full px-1.5 py-0.5"
                              title={`${linkCount} linked evidence item${linkCount !== 1 ? "s" : ""}`}
                            >
                              <Link2 size={10} />
                              {linkCount}
                            </span>
                          )}
                          {linkCount === 0 && section.id !== "nuggets" && (
                            <span
                              className="shrink-0 inline-flex items-center gap-0.5 text-[10px] text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-800 rounded-full px-1.5 py-0.5"
                              title="No linked evidence"
                            >
                              <Link2 size={10} />
                              0
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-2">
                          {item.confidence !== undefined && (
                            <span className={cn("text-xs", confidenceColor(item.confidence))}>
                              Confidence: {Math.round(item.confidence * 100)}%
                            </span>
                          )}
                          {item.impact && (
                            <span className="text-xs text-slate-500">
                              Impact: {item.impact}
                            </span>
                          )}
                          {item.priority && (
                            <span className="text-xs text-slate-500">
                              Priority: {item.priority}
                            </span>
                          )}
                          {item.source && (
                            <span className="text-xs text-slate-400">
                              📄 {(item.source ?? "").split("/").pop() ?? item.source}
                            </span>
                          )}
                          {item.tags && item.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {item.tags.filter((t: string) => t.startsWith("ux-law:")).map((tag: string) => (
                                <LawBadge
                                  key={tag}
                                  lawId={tag.replace("ux-law:", "")}
                                  lawName={tag.replace("ux-law:", "").replace(/-/g, " ")}
                                />
                              ))}
                              {item.tags.filter((t: string) => !t.startsWith("ux-law:")).map((tag: string, i: number) => (
                                <span
                                  key={i}
                                  className="text-xs bg-slate-200 dark:bg-slate-700 rounded px-1 py-0.5"
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Atomic Research Drill-Down Modal */}
      {drilldownFinding && activeProjectId && (
        <AtomicDrilldown
          projectId={activeProjectId}
          finding={drilldownFinding}
          onClose={() => setDrilldownFinding(null)}
        />
      )}
      </>
      )}
    </div>
  );
}
