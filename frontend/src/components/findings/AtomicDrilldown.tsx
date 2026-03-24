"use client";

import { useEffect, useState, useCallback } from "react";
import {
  ArrowLeft,
  Target,
  Lightbulb,
  FileText,
  Sparkles,
  ChevronRight,
  ExternalLink,
  Link2,
  Search,
  Plus,
  X,
} from "lucide-react";
import { findings as findingsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Nugget, Fact, Insight, Recommendation } from "@/lib/types";

interface AtomicDrilldownProps {
  projectId: string;
  /** The finding to drill into */
  finding: {
    id: string;
    type: "recommendation" | "insight" | "fact" | "nugget";
    text: string;
  };
  onClose: () => void;
}

type FindingType = "recommendation" | "insight" | "fact" | "nugget";

interface ChainData {
  recommendation: Recommendation[];
  insight: Insight[];
  fact: Fact[];
  nugget: Nugget[];
}

const EMPTY_CHAIN: ChainData = { recommendation: [], insight: [], fact: [], nugget: [] };

/** Map finding types to what can be linked TO them */
const LINKABLE_TYPES: Record<FindingType, { linkType: FindingType; label: string } | null> = {
  recommendation: { linkType: "insight", label: "Insights" },
  insight: { linkType: "fact", label: "Facts" },
  fact: { linkType: "nugget", label: "Nuggets" },
  nugget: null, // nuggets are the base — nothing links below them
};

export default function AtomicDrilldown({ projectId, finding: initialFinding, onClose }: AtomicDrilldownProps) {
  const [activeFinding, setActiveFinding] = useState(initialFinding);
  const [chain, setChain] = useState<ChainData>(EMPTY_CHAIN);
  const [loading, setLoading] = useState(true);
  // Navigation history for breadcrumb traversal
  const [history, setHistory] = useState<Array<{ id: string; type: FindingType; text: string }>>([initialFinding]);
  // Link evidence state
  const [showLinkPanel, setShowLinkPanel] = useState(false);
  const [linkSearch, setLinkSearch] = useState("");
  const [linkCandidates, setLinkCandidates] = useState<Array<{ id: string; text: string; type: FindingType }>>([]);
  const [linkLoading, setLinkLoading] = useState(false);
  const [linkingId, setLinkingId] = useState<string | null>(null);

  const loadChain = useCallback(async (type: string, id: string) => {
    setLoading(true);
    try {
      const result = await findingsApi.evidenceChain(type, id);
      setChain(result.chain || EMPTY_CHAIN);
    } catch {
      // Fallback: load all findings and try local linking
      try {
        const [nuggets, facts, insights, recs] = await Promise.all([
          findingsApi.nuggets(projectId),
          findingsApi.facts(projectId),
          findingsApi.insights(projectId),
          findingsApi.recommendations(projectId),
        ]);
        setChain(buildLocalChain({ id, type }, recs, insights, facts, nuggets));
      } catch {
        setChain(EMPTY_CHAIN);
      }
    }
    setLoading(false);
  }, [projectId]);

  useEffect(() => {
    loadChain(activeFinding.type, activeFinding.id);
  }, [activeFinding, loadChain]);

  // Load linkable candidates when link panel opens
  const loadLinkCandidates = useCallback(async () => {
    const linkInfo = LINKABLE_TYPES[activeFinding.type];
    if (!linkInfo) return;

    setLinkLoading(true);
    try {
      const fetchMap: Record<string, () => Promise<any[]>> = {
        nugget: () => findingsApi.nuggets(projectId),
        fact: () => findingsApi.facts(projectId),
        insight: () => findingsApi.insights(projectId),
        recommendation: () => findingsApi.recommendations(projectId),
      };
      const items = await fetchMap[linkInfo.linkType]();
      // Exclude items already in the chain
      const existingIds = new Set(chain[linkInfo.linkType].map((c: any) => c.id));
      setLinkCandidates(
        items
          .filter((item: any) => !existingIds.has(item.id))
          .map((item: any) => ({ id: item.id, text: item.text, type: linkInfo.linkType }))
      );
    } catch {
      setLinkCandidates([]);
    }
    setLinkLoading(false);
  }, [activeFinding.type, projectId, chain]);

  useEffect(() => {
    if (showLinkPanel) {
      loadLinkCandidates();
    }
  }, [showLinkPanel, loadLinkCandidates]);

  const handleLink = async (linkId: string) => {
    const linkInfo = LINKABLE_TYPES[activeFinding.type];
    if (!linkInfo) return;

    setLinkingId(linkId);
    try {
      await findingsApi.linkEvidence(activeFinding.type, activeFinding.id, linkId, linkInfo.linkType);
      // Refresh the chain to show the new link
      await loadChain(activeFinding.type, activeFinding.id);
      // Remove the linked item from candidates
      setLinkCandidates((prev) => prev.filter((c) => c.id !== linkId));
    } catch (err) {
      console.error("Failed to link evidence:", err);
    }
    setLinkingId(null);
  };

  const filteredCandidates = linkCandidates.filter(
    (c) => !linkSearch || c.text.toLowerCase().includes(linkSearch.toLowerCase())
  );

  // Navigate to a different finding in the chain
  const drillTo = (type: FindingType, item: { id: string; text: string }) => {
    const newFinding = { id: item.id, type, text: item.text };
    setHistory((prev) => [...prev, newFinding]);
    setActiveFinding(newFinding);
  };

  // Breadcrumb navigation — click a level to filter to that type
  const breadcrumbLevels: { type: FindingType; label: string; icon: string }[] = [
    { type: "recommendation", label: "Recommendations", icon: "🎯" },
    { type: "insight", label: "Insights", icon: "💡" },
    { type: "fact", label: "Facts", icon: "📄" },
    { type: "nugget", label: "Nuggets", icon: "✨" },
  ];

  const jumpToLevel = (type: FindingType) => {
    // Find the first item of that type in the chain
    const items = chain[type];
    if (items.length > 0) {
      drillTo(type, items[0] as any);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-3 p-4 border-b border-slate-200 dark:border-slate-700">
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">
              Atomic Research — Evidence Chain
            </h3>
            <p className="text-xs text-slate-500">
              Trace from recommendations down to raw evidence
            </p>
          </div>
        </div>

        {/* Chain visualization */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Clickable Breadcrumb */}
          <div className="flex items-center gap-1 text-xs text-slate-400 mb-6 flex-wrap">
            {breadcrumbLevels.map((level, idx) => {
              const isActive = activeFinding.type === level.type;
              const hasItems = chain[level.type]?.length > 0;
              return (
                <span key={level.type} className="flex items-center gap-1">
                  {idx > 0 && <ChevronRight size={12} />}
                  <button
                    onClick={() => hasItems && jumpToLevel(level.type)}
                    disabled={!hasItems}
                    className={cn(
                      "px-1.5 py-0.5 rounded transition-colors",
                      isActive
                        ? "text-reclaw-600 font-semibold bg-reclaw-50 dark:bg-reclaw-900/20"
                        : hasItems
                          ? "hover:text-reclaw-500 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
                          : "opacity-40 cursor-default"
                    )}
                  >
                    {level.icon} {level.label}
                    {hasItems && (
                      <span className="ml-1 text-[10px] text-slate-400">
                        ({chain[level.type].length})
                      </span>
                    )}
                  </button>
                </span>
              );
            })}
            <ChevronRight size={12} />
            <span className="opacity-40">📁 Sources</span>
          </div>

          {loading ? (
            <div className="text-center py-8 text-slate-400 text-sm">Loading evidence chain...</div>
          ) : (
            <>
              {/* The selected finding (highlighted) */}
              <div className="mb-6">
                <ChainLevel
                  icon={getIcon(activeFinding.type)}
                  label={activeFinding.type.charAt(0).toUpperCase() + activeFinding.type.slice(1)}
                  color={getColor(activeFinding.type)}
                  highlighted
                >
                  <div className="p-3 rounded-lg bg-reclaw-50 dark:bg-reclaw-900/20 border-2 border-reclaw-300 dark:border-reclaw-700">
                    <p className="text-sm text-slate-900 dark:text-white font-medium">
                      {activeFinding.text}
                    </p>
                    {LINKABLE_TYPES[activeFinding.type] && (
                      <button
                        onClick={() => setShowLinkPanel(!showLinkPanel)}
                        className={cn(
                          "mt-2 inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md transition-colors",
                          showLinkPanel
                            ? "bg-reclaw-600 text-white"
                            : "bg-white dark:bg-slate-800 text-reclaw-600 border border-reclaw-300 dark:border-reclaw-700 hover:bg-reclaw-50 dark:hover:bg-reclaw-900/30"
                        )}
                      >
                        {showLinkPanel ? <X size={12} /> : <Link2 size={12} />}
                        {showLinkPanel ? "Close" : `Link ${LINKABLE_TYPES[activeFinding.type]!.label}`}
                      </button>
                    )}
                  </div>
                </ChainLevel>
              </div>

              {/* Link Evidence Panel */}
              {showLinkPanel && LINKABLE_TYPES[activeFinding.type] && (
                <div className="mb-6 ml-8 border border-reclaw-200 dark:border-reclaw-800 rounded-lg bg-reclaw-50/50 dark:bg-reclaw-900/10 p-3">
                  <div className="flex items-center gap-2 mb-3">
                    <Search size={14} className="text-slate-400" />
                    <input
                      type="text"
                      placeholder={`Search ${LINKABLE_TYPES[activeFinding.type]!.label.toLowerCase()} to link...`}
                      value={linkSearch}
                      onChange={(e) => setLinkSearch(e.target.value)}
                      className="flex-1 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-reclaw-400"
                    />
                  </div>
                  <div className="max-h-48 overflow-y-auto space-y-1.5">
                    {linkLoading ? (
                      <p className="text-xs text-slate-400 text-center py-3">Loading candidates...</p>
                    ) : filteredCandidates.length === 0 ? (
                      <p className="text-xs text-slate-400 text-center py-3">
                        {linkSearch ? "No matching items found." : `No unlinked ${LINKABLE_TYPES[activeFinding.type]!.label.toLowerCase()} available.`}
                      </p>
                    ) : (
                      filteredCandidates.map((candidate) => (
                        <div
                          key={candidate.id}
                          className="flex items-start gap-2 p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
                        >
                          <p className="flex-1 text-xs text-slate-700 dark:text-slate-300 line-clamp-2">
                            {candidate.text}
                          </p>
                          <button
                            onClick={() => handleLink(candidate.id)}
                            disabled={linkingId === candidate.id}
                            className="shrink-0 inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-reclaw-600 text-white hover:bg-reclaw-700 disabled:opacity-50 transition-colors"
                          >
                            {linkingId === candidate.id ? (
                              "Linking..."
                            ) : (
                              <>
                                <Plus size={10} /> Link
                              </>
                            )}
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* Supporting evidence — show levels OTHER than the active one */}
              {activeFinding.type !== "recommendation" && chain.recommendation.length > 0 && (
                <ChainLevel icon={Target} label="Recommendations" color="text-green-600">
                  {chain.recommendation.map((r: any) => (
                    <EvidenceCard
                      key={r.id}
                      text={r.text}
                      badges={[r.priority, r.effort].filter(Boolean)}
                      onClick={() => drillTo("recommendation", r)}
                    />
                  ))}
                </ChainLevel>
              )}

              {activeFinding.type !== "insight" && chain.insight.length > 0 && (
                <ChainLevel icon={Lightbulb} label="Insights" color="text-yellow-600">
                  {chain.insight.map((i: any) => (
                    <EvidenceCard
                      key={i.id}
                      text={i.text}
                      badges={[
                        i.confidence != null ? `${Math.round(i.confidence * 100)}% confidence` : "",
                        i.impact,
                      ].filter(Boolean)}
                      onClick={() => drillTo("insight", i)}
                    />
                  ))}
                </ChainLevel>
              )}

              {activeFinding.type !== "fact" && chain.fact.length > 0 && (
                <ChainLevel icon={FileText} label="Facts" color="text-blue-600">
                  {chain.fact.map((f: any) => (
                    <EvidenceCard
                      key={f.id}
                      text={f.text}
                      onClick={() => drillTo("fact", f)}
                    />
                  ))}
                </ChainLevel>
              )}

              {activeFinding.type !== "nugget" && chain.nugget.length > 0 && (
                <ChainLevel icon={Sparkles} label="Nuggets (Raw Evidence)" color="text-purple-600">
                  {chain.nugget.map((n: any) => (
                    <EvidenceCard
                      key={n.id}
                      text={n.text}
                      source={n.source}
                      sourceLocation={n.source_location}
                      tags={n.tags}
                      onClick={() => drillTo("nugget", n)}
                    />
                  ))}
                </ChainLevel>
              )}

              {/* If we're at nugget level, show source */}
              {activeFinding.type === "nugget" && chain.nugget.length > 0 && (
                <ChainLevel icon={ExternalLink} label="Source" color="text-slate-600">
                  {chain.nugget
                    .filter((n: any) => n.id === activeFinding.id)
                    .map((n: any) => (
                      <div key={n.id} className="text-sm text-slate-600 dark:text-slate-400">
                        <p>
                          📁 <span className="font-mono">{n.source}</span>
                        </p>
                        {n.source_location && <p className="text-xs">@ {n.source_location}</p>}
                      </div>
                    ))}
                </ChainLevel>
              )}

              {/* Empty state — only show if NO linked evidence at all */}
              {chain.insight.length === 0 &&
                chain.fact.length === 0 &&
                chain.nugget.length === 0 &&
                chain.recommendation.length === 0 && (
                  <div className="text-center py-8">
                    <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
                      No linked evidence chain yet.
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Link this {activeFinding.type} to supporting evidence to build the atomic research path.
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      The research chain tracks how information flows: Nuggets → Facts → Insights → Recommendations
                    </p>

                    {/* Atomic research chain diagram */}
                    <div className="mt-5 inline-flex flex-col items-center gap-0">
                      {[
                        { label: "Recommendation", desc: "Actionable next step", color: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800", icon: "🎯" },
                        { label: "Insight", desc: "Pattern or theme identified", color: "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800", icon: "💡" },
                        { label: "Fact", desc: "Verified claim from evidence", color: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800", icon: "📄" },
                        { label: "Nugget", desc: "Raw quote or observation", color: "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-800", icon: "✨" },
                      ].map((level, idx) => (
                        <div key={level.label} className="flex flex-col items-center">
                          {idx > 0 && (
                            <div className="w-px h-3 bg-slate-300 dark:bg-slate-600" />
                          )}
                          <div
                            className={cn(
                              "flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-medium",
                              level.color,
                              activeFinding.type === level.label.toLowerCase() && "ring-2 ring-reclaw-400 ring-offset-1"
                            )}
                          >
                            <span>{level.icon}</span>
                            <span>{level.label}</span>
                            <span className="font-normal opacity-70">— {level.desc}</span>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Link Evidence CTA */}
                    {LINKABLE_TYPES[activeFinding.type] && (
                      <button
                        onClick={() => setShowLinkPanel(true)}
                        className="mt-5 inline-flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg bg-reclaw-600 text-white hover:bg-reclaw-700 transition-colors"
                      >
                        <Link2 size={14} />
                        Link {LINKABLE_TYPES[activeFinding.type]!.label}
                      </button>
                    )}
                  </div>
                )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// --- Helpers ---

/** Local fallback chain builder when API endpoint isn't available */
function buildLocalChain(
  finding: { id: string; type: string },
  recs: Recommendation[],
  insights: Insight[],
  facts: Fact[],
  nuggets: Nugget[]
): ChainData {
  const parseIds = (json: string | string[]): string[] => {
    if (Array.isArray(json)) return json;
    if (!json) return [];
    try { return JSON.parse(json); } catch { return []; }
  };

  switch (finding.type) {
    case "recommendation": {
      const rec = recs.find((r) => r.id === finding.id);
      const linkedInsightIds = rec ? parseIds(rec.insight_ids) : [];
      const linkedInsights = linkedInsightIds.length > 0
        ? insights.filter((i) => linkedInsightIds.includes(i.id))
        : [];
      const allFactIds = linkedInsights.flatMap((i) => parseIds(i.fact_ids));
      const linkedFacts = allFactIds.length > 0
        ? facts.filter((f) => allFactIds.includes(f.id))
        : [];
      const allNuggetIds = linkedFacts.flatMap((f) => parseIds(f.nugget_ids));
      const linkedNuggets = allNuggetIds.length > 0
        ? nuggets.filter((n) => allNuggetIds.includes(n.id))
        : [];
      return { recommendation: rec ? [rec] : [], insight: linkedInsights, fact: linkedFacts, nugget: linkedNuggets };
    }
    case "insight": {
      const insight = insights.find((i) => i.id === finding.id);
      const linkedFactIds = insight ? parseIds(insight.fact_ids) : [];
      const linkedFacts = linkedFactIds.length > 0
        ? facts.filter((f) => linkedFactIds.includes(f.id))
        : [];
      const allNuggetIds = linkedFacts.flatMap((f) => parseIds(f.nugget_ids));
      const linkedNuggets = allNuggetIds.length > 0
        ? nuggets.filter((n) => allNuggetIds.includes(n.id))
        : [];
      const linkedRecs = recs.filter((r) => parseIds(r.insight_ids).includes(finding.id));
      return { recommendation: linkedRecs, insight: insight ? [insight] : [], fact: linkedFacts, nugget: linkedNuggets };
    }
    case "fact": {
      const fact = facts.find((f) => f.id === finding.id);
      const linkedNuggetIds = fact ? parseIds(fact.nugget_ids) : [];
      const linkedNuggets = linkedNuggetIds.length > 0
        ? nuggets.filter((n) => linkedNuggetIds.includes(n.id))
        : [];
      const linkedInsights = insights.filter((i) => parseIds(i.fact_ids).includes(finding.id));
      const insightIdSet = new Set(linkedInsights.map((i) => i.id));
      const linkedRecs = recs.filter((r) => parseIds(r.insight_ids).some((id) => insightIdSet.has(id)));
      return { recommendation: linkedRecs, insight: linkedInsights, fact: fact ? [fact] : [], nugget: linkedNuggets };
    }
    case "nugget": {
      const linkedFacts = facts.filter((f) => parseIds(f.nugget_ids).includes(finding.id));
      const factIdSet = new Set(linkedFacts.map((f) => f.id));
      const linkedInsights = insights.filter((i) => parseIds(i.fact_ids).some((id) => factIdSet.has(id)));
      const insightIdSet = new Set(linkedInsights.map((i) => i.id));
      const linkedRecs = recs.filter((r) => parseIds(r.insight_ids).some((id) => insightIdSet.has(id)));
      const nugget = nuggets.find((n) => n.id === finding.id);
      return { recommendation: linkedRecs, insight: linkedInsights, fact: linkedFacts, nugget: nugget ? [nugget] : [] };
    }
    default:
      return EMPTY_CHAIN;
  }
}

function getIcon(type: string) {
  switch (type) {
    case "recommendation": return Target;
    case "insight": return Lightbulb;
    case "fact": return FileText;
    case "nugget": return Sparkles;
    default: return FileText;
  }
}

function getColor(type: string) {
  switch (type) {
    case "recommendation": return "text-green-600";
    case "insight": return "text-yellow-600";
    case "fact": return "text-blue-600";
    case "nugget": return "text-purple-600";
    default: return "text-slate-600";
  }
}

function ChainLevel({
  icon: Icon,
  label,
  color,
  highlighted,
  children,
}: {
  icon: any;
  label: string;
  color: string;
  highlighted?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("mb-4", highlighted && "")}>
      <div className="flex items-center gap-2 mb-2">
        <div className={cn("w-6 h-6 rounded-full flex items-center justify-center", highlighted ? "bg-reclaw-100" : "bg-slate-100 dark:bg-slate-800")}>
          <Icon size={14} className={color} />
        </div>
        <h4 className={cn("text-xs font-semibold uppercase", color)}>{label}</h4>
      </div>
      <div className="ml-8 space-y-1.5">{children}</div>
    </div>
  );
}

function EvidenceCard({
  text,
  source,
  sourceLocation,
  badges,
  tags,
  onClick,
}: {
  text: string;
  source?: string;
  sourceLocation?: string;
  badges?: string[];
  tags?: string[];
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "p-2.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700",
        onClick && "cursor-pointer hover:border-reclaw-300 dark:hover:border-reclaw-700 hover:shadow-sm transition-all"
      )}
    >
      <p className="text-xs text-slate-700 dark:text-slate-300">{text}</p>
      <div className="flex items-center gap-2 mt-1.5 flex-wrap">
        {source && (
          <span className="text-[10px] text-slate-400">
            📄 {source.split("/").pop()}
            {sourceLocation && ` @ ${sourceLocation}`}
          </span>
        )}
        {badges?.filter(Boolean).map((badge, i) => (
          <span
            key={i}
            className="text-[10px] bg-slate-100 dark:bg-slate-700 rounded px-1 py-0.5 text-slate-500"
          >
            {badge}
          </span>
        ))}
        {tags?.map((tag, i) => (
          <span
            key={i}
            className="text-[10px] bg-purple-100 dark:bg-purple-900/30 rounded px-1 py-0.5 text-purple-600 dark:text-purple-400"
          >
            {tag}
          </span>
        ))}
        {onClick && (
          <span className="text-[10px] text-reclaw-500 ml-auto">Click to drill in →</span>
        )}
      </div>
    </div>
  );
}
