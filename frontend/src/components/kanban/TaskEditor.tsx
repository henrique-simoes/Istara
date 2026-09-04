"use client";

import { forwardRef, useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { AlertTriangle, Bot, CheckCircle2, ClipboardList, FileStack, FileText, Globe, Network, Plus, RotateCcw, Save, Send, ShieldCheck, Tags, Trash2, User, X, Zap } from "lucide-react";
import { useTaskStore } from "@/stores/taskStore";
import { useProjectStore } from "@/stores/projectStore";
import { documents as documentsApi, taskLocking, tasks as tasksApi } from "@/lib/api";
import { researchValidity } from "@/lib/researchIntegrityApi";
import { loadTaskDocumentReferences, resolveTaskDocumentTitle } from "@/lib/taskDocumentTitles";
import type { EvidenceGraphTraceabilityType, Task, TaskAtomicPath, TaskQualitySummary } from "@/lib/types";

const SKILL_OPTIONS = [
  { value: "", label: "Auto-detect" },
  { value: "user-interviews", label: "User Interviews" },
  { value: "thematic-analysis", label: "Thematic Analysis" },
  { value: "affinity-mapping", label: "Affinity Mapping" },
  { value: "persona-creation", label: "Persona Creation" },
  { value: "journey-mapping", label: "Journey Mapping" },
  { value: "usability-testing", label: "Usability Testing" },
  { value: "competitive-analysis", label: "Competitive Analysis" },
  { value: "survey-design", label: "Survey Design" },
  { value: "heuristic-evaluation", label: "Heuristic Evaluation" },
  { value: "research-synthesis", label: "Research Synthesis" },
  { value: "survey-generator", label: "Survey Generator" },
  { value: "interview-question-generator", label: "Interview Questions" },
  { value: "taxonomy-generator", label: "Taxonomy Generator" },
  { value: "kappa-thematic-analysis", label: "Kappa Analysis" },
];

const LABEL_COLORS = ["#64748b", "#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed"];

const SYSTEM_TAG_DESCRIPTIONS: Record<string, string> = {
  evidence: "Evidence-related task. Agents should preserve source traceability and quote/document support.",
  source: "Source-related task. Check files, citations, links, or source coverage.",
  citation: "Citation-related task. Verify references and source attribution.",
  unsupported: "Unsupported-claim tag. Review for claims that need stronger evidence.",
  nugget: "Nugget-related task. Work touches source evidence extracted from research material.",
  instruction: "Instruction-following tag. Agents should pay close attention to the user's directives.",
  method: "Methodology tag. Review or apply the correct research method or skill.",
  specialist: "Specialist-routing tag. The task may need a more suitable agent or domain expert.",
  hallucination: "Hallucination risk. Validate claims carefully against project evidence.",
  synthesis: "Synthesis tag. Work involves facts, insights, recommendations, or patterns.",
  document: "Document tag. Work depends on uploaded research files.",
  file: "File tag. Work depends on attached or generated files.",
  url: "URL/tool tag. Work depends on web links, fetching, or external tools.",
  website: "Website/tool tag. Check page access, fetching, or browser-derived evidence.",
  browser: "Browser/tool tag. Work may require browser inspection or web capture.",
  validation: "Validation tag. Check consensus, review, or quality gates.",
  consensus: "Consensus tag. Multi-model or agent agreement may be relevant.",
  requirement: "Requirement-change tag. The user changed scope or acceptance criteria.",
  unclear: "Ambiguous task tag. Clarify requirements before agents continue.",
  ambiguous: "Ambiguous task tag. The task needs clearer instructions.",
  "missing_evidence": "System tag: revision was classified as missing supporting evidence.",
  "ignored_user_instructions": "System tag: revision was classified as not following user instructions.",
  "wrong_skill": "System tag: revision was classified as using the wrong skill or method.",
  "wrong_agent": "System tag: revision was classified as needing a different agent.",
  "hallucination_or_unsupported_claim": "System tag: revision was classified as hallucination or unsupported claim risk.",
  "bad_synthesis": "System tag: revision was classified as weak synthesis.",
  "insufficient_documents": "System tag: revision was classified as missing or insufficient input documents.",
  "url_or_tool_failure": "System tag: revision was classified as a URL, browser, or tool failure.",
  "validation_false_positive": "System tag: validation accepted work the user later rejected.",
  "user_changed_requirements": "System tag: user changed requirements after earlier work.",
  "unclear_task": "System tag: task was classified as ambiguous or under-specified.",
};

function normalizeTagName(label: Task["labels"][number]) {
  return (typeof label === "string" ? label : label.name || "").trim();
}

function isSystemTag(label: Task["labels"][number]) {
  if (typeof label !== "string" && label.kind === "system") return true;
  const name = normalizeTagName(label).toLowerCase();
  return name in SYSTEM_TAG_DESCRIPTIONS || name.startsWith("system:") || name.startsWith("review:");
}

function tagDescription(label: Task["labels"][number]) {
  const name = normalizeTagName(label);
  const normalized = name.toLowerCase().replace(/^system:/, "").replace(/^review:/, "");
  if (typeof label !== "string" && label.kind === "system") {
    return SYSTEM_TAG_DESCRIPTIONS[normalized] || `System tag: ${name}. Istara uses this tag for routing, review, or telemetry.`;
  }
  return SYSTEM_TAG_DESCRIPTIONS[normalized] || "User task label. Click to remove it from this task.";
}

function tagColor(label: Task["labels"][number]) {
  if (isSystemTag(label)) return "#475569";
  return typeof label === "string" ? "#64748b" : label.color || "#64748b";
}

interface TaskEditorProps {
  task: Task;
  onClose: () => void;
}

export default function TaskEditor({ task, onClose }: TaskEditorProps) {
  const { updateTask, approveTask, requestRevision } = useTaskStore();
  const { activeProjectId } = useProjectStore();
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description);
  const [skillName, setSkillName] = useState(task.skill_name);
  const [userContext, setUserContext] = useState(task.user_context);
  const [instructions, setInstructions] = useState(task.instructions || "");
  const [urls, setUrls] = useState<string[]>(task.urls || []);
  const [newUrl, setNewUrl] = useState("");
  const [labels, setLabels] = useState<Task["labels"]>(task.labels || []);
  const [newLabel, setNewLabel] = useState("");
  const [inputDocs, setInputDocs] = useState<string[]>(task.input_document_ids || []);
  const [outputDocs, setOutputDocs] = useState<string[]>(task.output_document_ids || []);
  const [projectDocuments, setProjectDocuments] = useState<{ id: string; title: string }[]>([]);
  const [showDocPicker, setShowDocPicker] = useState<"input" | "output" | null>(null);
  const [docsLoading, setDocsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [whatToReview, setWhatToReview] = useState(task.what_to_review || task.last_review_feedback || "");
  const [revisionTarget, setRevisionTarget] = useState<"backlog" | "in_progress">("backlog");
  const [quality, setQuality] = useState<TaskQualitySummary | null>(null);
  const [atomicPath, setAtomicPath] = useState<TaskAtomicPath | null>(null);
  const [traceability, setTraceability] = useState<EvidenceGraphTraceabilityType | null>(null);
  const [traceabilityLoading, setTraceabilityLoading] = useState(false);
  const [codingRunLoading, setCodingRunLoading] = useState(false);
  const [codingRunError, setCodingRunError] = useState("");
  const docPickerRef = useRef<HTMLDivElement>(null);
  const closingRef = useRef(false);
  const hasActiveTaskProject = Boolean(activeProjectId && activeProjectId === task.project_id);
  const hasAttachedDocuments = inputDocs.length > 0 || outputDocs.length > 0;

  const saveDraft = useCallback(async () => {
    if (saving || !activeProjectId || activeProjectId !== task.project_id) return false;
    setSaving(true);
    setSaveError("");
    try {
      await updateTask(task.id, {
        title,
        description,
        skill_name: skillName,
        user_context: userContext,
        instructions,
        urls,
        labels,
        what_to_review: whatToReview,
        input_document_ids: inputDocs,
        output_document_ids: outputDocs,
      }, activeProjectId);
      return true;
    } catch (e) {
      console.error("Failed to save task:", e);
      setSaveError(e instanceof Error ? e.message : "Istara could not save this task.");
      return false;
    } finally {
      setSaving(false);
    }
  }, [activeProjectId, description, inputDocs, instructions, labels, outputDocs, saving, skillName, task.id, task.project_id, title, updateTask, urls, userContext, whatToReview]);

  const releaseLock = useCallback(async () => {
    if (!activeProjectId || activeProjectId !== task.project_id) return false;
    try {
      await taskLocking.unlock(task.id, activeProjectId);
      return true;
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Istara could not release the editing lock.");
      return false;
    }
  }, [activeProjectId, task.id, task.project_id]);

  const closeWithSave = useCallback(async () => {
    if (closingRef.current) return;
    closingRef.current = true;
    const saved = await saveDraft();
    if (!saved || !(await releaseLock())) {
      closingRef.current = false;
      return;
    }
    onClose();
  }, [onClose, releaseLock, saveDraft]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeWithSave();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [closeWithSave]);

  const refreshReviewEvidence = useCallback(() => {
    if (!activeProjectId || activeProjectId !== task.project_id) {
      setQuality(null);
      setAtomicPath(null);
      setTraceability(null);
      setTraceabilityLoading(false);
      return;
    }
    tasksApi.qualitySummary(task.id, activeProjectId).then(setQuality).catch(() => setQuality(null));
    tasksApi.atomicPath(task.id, activeProjectId).then(setAtomicPath).catch(() => setAtomicPath(null));
    setTraceabilityLoading(true);
    researchValidity.traceability(activeProjectId, { taskId: task.id, limit: 25 })
      .then(setTraceability)
      .catch(() => setTraceability(null))
      .finally(() => setTraceabilityLoading(false));
  }, [activeProjectId, task.id, task.project_id]);

  useEffect(() => {
    refreshReviewEvidence();
  }, [refreshReviewEvidence]);

  const startCodingRun = useCallback(async () => {
    if (!activeProjectId || activeProjectId !== task.project_id) return;
    setCodingRunLoading(true);
    setCodingRunError("");
    try {
      await researchValidity.startCodingRun(activeProjectId, { task_id: task.id });
      refreshReviewEvidence();
    } catch (e) {
      setCodingRunError(e instanceof Error ? e.message : "Coding run failed");
    } finally {
      setCodingRunLoading(false);
    }
  }, [activeProjectId, refreshReviewEvidence, task.id, task.project_id]);

  useEffect(() => {
    // Resolve attached document titles as soon as a task is reopened. Loading
    // only after opening the picker left existing chips displaying UUIDs.
    if (
      !activeProjectId ||
      activeProjectId !== task.project_id ||
      (!showDocPicker && !hasAttachedDocuments)
    ) {
      if (!hasAttachedDocuments) setProjectDocuments([]);
      return;
    }
    let cancelled = false;
    setProjectDocuments([]);
    setDocsLoading(true);
    loadTaskDocumentReferences(
      documentsApi,
      activeProjectId,
      [...inputDocs, ...outputDocs],
    )
      .then((documents) => {
        if (!cancelled) setProjectDocuments(documents);
      })
      .finally(() => {
        if (!cancelled) setDocsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeProjectId, hasAttachedDocuments, inputDocs, outputDocs, showDocPicker, task.project_id]);

  useEffect(() => {
    if (!showDocPicker) return;
    const handler = (e: MouseEvent) => {
      if (docPickerRef.current && !docPickerRef.current.contains(e.target as Node)) setShowDocPicker(null);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showDocPicker]);

  const getDocTitle = (docId: string) => {
    return resolveTaskDocumentTitle(projectDocuments, docId, docsLoading);
  };
  const addDocument = (docId: string, target: "input" | "output") => {
    if (target === "input" && !inputDocs.includes(docId)) setInputDocs([...inputDocs, docId]);
    if (target === "output" && !outputDocs.includes(docId)) setOutputDocs([...outputDocs, docId]);
    setShowDocPicker(null);
  };
  const addUrl = () => {
    const trimmed = newUrl.trim();
    if (trimmed && !urls.includes(trimmed)) setUrls([...urls, trimmed]);
    setNewUrl("");
  };
  const addLabel = () => {
    const name = newLabel.trim();
    if (!name) return;
    const color = LABEL_COLORS[labels.length % LABEL_COLORS.length];
    setLabels([...labels, { name, color, kind: "task" }]);
    setNewLabel("");
  };
  const labelName = normalizeTagName;

  const approve = async () => {
    if (!activeProjectId || activeProjectId !== task.project_id) return;
    if (!(await saveDraft())) return;
    try {
      await approveTask(task.id, activeProjectId, whatToReview || "Human approved task output.");
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Istara could not approve this task.");
      return;
    }
    if (!(await releaseLock())) return;
    onClose();
  };
  const flagRevision = async () => {
    if (!activeProjectId || activeProjectId !== task.project_id) return;
    if (!(await saveDraft())) return;
    try {
      await requestRevision(task.id, {
        what_to_review: whatToReview,
        next_status: revisionTarget,
        labels,
        skill_name: skillName,
        input_document_ids: inputDocs,
        urls,
      }, activeProjectId);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Istara could not request a revision.");
      return;
    }
    if (!(await releaseLock())) return;
    onClose();
  };
  const sendReport = async () => {
    if (!activeProjectId || activeProjectId !== task.project_id) return;
    if (!(await saveDraft())) return;
    try {
      await tasksApi.createReport(task.id, activeProjectId);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Istara could not create the report.");
      return;
    }
    if (!(await releaseLock())) return;
    onClose();
  };

  const canReview = task.status === "in_review" || task.status === "done";
  const requiresWhatToReview = canReview && task.review_state !== "approved";
  const systemStatusTags = [
    { name: task.status.replace(/_/g, " "), description: "Current Kanban state for this task." },
    task.review_state && task.review_state !== "none"
      ? { name: task.review_state.replace(/_/g, " "), description: "Current human review state for this task." }
      : null,
    task.review_failure_category
      ? { name: task.review_failure_category.replace(/_/g, " "), description: tagDescription({ name: task.review_failure_category, kind: "system" }) }
      : null,
    task.next_agent_action
      ? { name: task.next_agent_action.replace(/_/g, " "), description: "Next action Istara will give the assigned agent." }
      : null,
  ].filter(Boolean) as Array<{ name: string; description: string }>;
  const researchValidityState = atomicPath?.research_validity;
  const latestCodingRun = researchValidityState?.latest_coding_run as Record<string, unknown> | null | undefined;
  const codeApplicationCount = researchValidityState?.code_application_count ?? 0;
  const acceptedCodeApplicationCount = researchValidityState?.accepted_code_application_count ?? 0;
  const hasResearchValidityRecords = Boolean((researchValidityState?.coding_run_count || 0) > 0 || codeApplicationCount > 0);
  const latestPromotionStatus = String(latestCodingRun?.promotion_status || "not coded");
  const latestReliabilityMethod =
    typeof latestCodingRun?.reliability_method === "string" && latestCodingRun.reliability_method
      ? latestCodingRun.reliability_method.replace(/_/g, " ")
      : "";
  const blockedReviewItems = researchValidityState?.blocked_or_review_items || [];
  const taskFindingCount =
    (atomicPath?.nuggets?.count ?? 0) +
    (atomicPath?.facts?.count ?? 0) +
    (atomicPath?.insights?.count ?? 0) +
    (atomicPath?.recommendations?.count ?? 0);
  const hasReportableTaskFindings = taskFindingCount > 0;
  const acceptedPromotionStatuses = ["accepted", "accepted_after_reconciliation"];
  const latestGateAccepted = acceptedPromotionStatuses.includes(latestPromotionStatus);
  const needsCodingBeforeReport = Boolean(atomicPath && hasReportableTaskFindings && codeApplicationCount === 0);
  const researchValidityBlocked = Boolean(
    needsCodingBeforeReport ||
    (hasResearchValidityRecords &&
      (!latestGateAccepted ||
        blockedReviewItems.some((item) => !acceptedPromotionStatuses.includes(item.promotion_status))))
  );
  const researchValidityReady = Boolean(
    hasReportableTaskFindings &&
    acceptedCodeApplicationCount > 0 &&
    !researchValidityBlocked
  );
  const canSendToReport = task.status === "done" && task.review_state === "approved" && researchValidityReady;
  const reportGateReason = !hasReportableTaskFindings
    ? "No task findings are available for reporting yet."
    : needsCodingBeforeReport
      ? "Run a coding pass and accept or reconcile coded evidence before reporting."
      : researchValidityBlocked
        ? "Resolve low-agreement or unreconciled coded evidence before reporting."
        : acceptedCodeApplicationCount === 0
          ? "Accept or reconcile coded evidence before reporting."
          : "";
  const doneGateReason = needsCodingBeforeReport
    ? "Run a coding pass and accept or reconcile coded evidence before marking this research task Done."
    : researchValidityBlocked
      ? "Resolve low-agreement or unreconciled coded evidence before marking this research task Done."
      : "";
  const canMarkDone = !researchValidityBlocked;
  const traceSummary = traceability?.summary || {};
  const traceReportDependencyCount = traceability?.report_dependencies?.length || 0;
  const traceLowAgreementCount = traceSummary.low_agreement_dependency_count || traceability?.low_agreement_dependencies?.length || 0;
  const traceReconciliationCount = traceSummary.reconciliation_decision_count || traceability?.reconciliation_decisions?.length || 0;
  const traceEdgeCount = traceSummary.evidence_graph_edge_count || traceability?.evidence_graph_edges?.length || 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) closeWithSave();
      }}
      role="presentation"
    >
      <div role="dialog" aria-modal="true" aria-labelledby="task-editor-title" className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-xl bg-white shadow-xl dark:bg-slate-900">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-5 py-4 dark:border-slate-700 dark:bg-slate-900">
          <div className="min-w-0">
            <h3 id="task-editor-title" className="truncate text-base font-semibold text-slate-900 dark:text-white">Task Details</h3>
            <p className="text-xs text-slate-500">Reserved from agents while editing. Saves before the dialog closes.</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">{saving ? "Saving..." : "Locked for editing"}</span>
            <button onClick={closeWithSave} className="rounded p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Close task editor"><X size={18} /></button>
          </div>
        </div>

        <div className="grid gap-5 overflow-y-auto p-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(340px,0.8fr)]">
          <div className="space-y-4">
            <Field label="Title">
              <input value={title} onChange={(e) => setTitle(e.target.value)} className="field-input text-base font-medium" />
            </Field>
            <Field label="Description">
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={5} className="field-input resize-y" />
            </Field>

            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Skill" icon={<Zap size={13} />}>
                <select value={skillName} onChange={(e) => setSkillName(e.target.value)} className="field-input">
                  {SKILL_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                </select>
              </Field>
              <Field label="Task Labels" icon={<Tags size={13} />}>
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-1.5">
                    {labels.map((label, idx) => (
                      <button
                        key={`${labelName(label)}-${idx}`}
                        onClick={() => setLabels(labels.filter((_, i) => i !== idx))}
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-white"
                        style={{ background: tagColor(label) }}
                        title={`${tagDescription(label)} Click to remove.`}
                      >
                        {isSystemTag(label) && <span className="text-[9px] uppercase opacity-80">system</span>}
                        <span>{labelName(label)}</span>
                      </button>
                    ))}
                    {labels.length === 0 && <span className="text-xs text-slate-400">No labels yet.</span>}
                  </div>
                  <div className="flex gap-2">
                    <input value={newLabel} onChange={(e) => setNewLabel(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addLabel(); } }} className="field-input min-w-0 flex-1" placeholder="Label" />
                    <IconButton onClick={addLabel} label="Add label"><Plus size={14} /></IconButton>
                  </div>
                </div>
              </Field>
            </div>

            <Field label="Specific Instructions" icon={<ClipboardList size={13} />}>
              <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} rows={4} className="field-input resize-y" />
            </Field>
            <Field label="Additional Context" icon={<User size={13} />}>
              <textarea value={userContext} onChange={(e) => setUserContext(e.target.value)} rows={5} className="field-input resize-y font-mono text-xs" />
            </Field>

            <div className="grid gap-4 md:grid-cols-2">
              <DocumentSection title="Input Documents" icon={<FileText size={13} />} docs={inputDocs} getDocTitle={getDocTitle} onRemove={(id) => setInputDocs(inputDocs.filter((doc) => doc !== id))} onPick={() => setShowDocPicker(showDocPicker === "input" ? null : "input")} picker={showDocPicker === "input" ? <DocumentPickerDropdown ref={docPickerRef} documents={projectDocuments} loading={docsLoading} excludeIds={inputDocs} onSelect={(id) => addDocument(id, "input")} /> : null} />
              <DocumentSection title="Output Documents" icon={<FileStack size={13} />} docs={outputDocs} getDocTitle={getDocTitle} onRemove={(id) => setOutputDocs(outputDocs.filter((doc) => doc !== id))} onPick={() => setShowDocPicker(showDocPicker === "output" ? null : "output")} picker={showDocPicker === "output" ? <DocumentPickerDropdown ref={docPickerRef} documents={projectDocuments} loading={docsLoading} excludeIds={outputDocs} onSelect={(id) => addDocument(id, "output")} /> : null} />
            </div>

            <Field label="URLs" icon={<Globe size={13} />}>
              <div className="space-y-2">
                {urls.map((url, idx) => (
                  <div key={url} className="flex items-center gap-2 rounded bg-slate-50 px-2 py-1 text-xs dark:bg-slate-800">
                    <span className="min-w-0 flex-1 truncate">{url}</span>
                    <IconButton onClick={() => setUrls(urls.filter((_, i) => i !== idx))} label="Remove URL"><Trash2 size={13} /></IconButton>
                  </div>
                ))}
                <div className="flex gap-2">
                  <input value={newUrl} onChange={(e) => setNewUrl(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addUrl(); } }} className="field-input min-w-0 flex-1" placeholder="https://example.com" />
                  <IconButton onClick={addUrl} label="Add URL"><Plus size={14} /></IconButton>
                </div>
              </div>
            </Field>

            {task.agent_notes && (
              <Field label="Agent Notes" icon={<Bot size={13} />}>
                <div className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-700 dark:bg-slate-800 dark:text-slate-300">{task.agent_notes}</div>
              </Field>
            )}
          </div>

          <aside className="space-y-4">
            <section className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <h4 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-slate-900 dark:text-white"><Tags size={14} /> Organization Tags</h4>
              <div className="flex flex-wrap gap-1.5">
                {labels.map((label, idx) => (
                  <span
                    key={`${labelName(label)}-summary-${idx}`}
                    className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-white"
                    style={{ background: tagColor(label) }}
                    title={tagDescription(label)}
                  >
                    {isSystemTag(label) && <span className="text-[9px] uppercase opacity-80">system</span>}
                    <span>{labelName(label)}</span>
                  </span>
                ))}
                {systemStatusTags.map((tag) => (
                  <span key={tag.name} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300" title={tag.description}>
                    {tag.name}
                  </span>
                ))}
                {labels.length === 0 && systemStatusTags.length === 0 && <span className="text-xs text-slate-400">No tags yet.</span>}
              </div>
              <p className="mt-2 text-xs text-slate-500">Hover over a tag to see what it means.</p>
            </section>

            <section className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <h4 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">Review</h4>
              {canReview ? (
                <div className="space-y-3">
                  <textarea value={whatToReview} onChange={(e) => setWhatToReview(e.target.value)} rows={6} className="field-input resize-y" placeholder="What should agents review, correct, repeat, or preserve?" />
                  {(quality?.recent_review_events?.length ?? 0) > 0 && (
                    <details className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/60">
                      <summary className="cursor-pointer text-xs font-medium text-slate-700 dark:text-slate-200">
                        Recent review history ({quality?.recent_review_events.length})
                      </summary>
                      <div className="mt-2 space-y-2" aria-label="Recent review history">
                        {quality?.recent_review_events.map((event) => (
                          <div key={event.id} className="rounded border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-900">
                            <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500">
                              <span className="font-medium uppercase tracking-wide">{event.outcome.replace(/_/g, " ")}</span>
                              <span>{event.created_by}</span>
                            </div>
                            <p className="mt-1 whitespace-pre-wrap text-xs text-slate-700 dark:text-slate-300">
                              {event.what_to_review || "No written instruction."}
                            </p>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                  <p className="text-xs font-medium text-slate-500">Send unsuccessful work back to:</p>
                  <div className="grid grid-cols-2 gap-2">
                    <button onClick={() => setRevisionTarget("backlog")} className={revisionTarget === "backlog" ? "review-choice-active" : "review-choice"}>Return to Backlog</button>
                    <button onClick={() => setRevisionTarget("in_progress")} className={revisionTarget === "in_progress" ? "review-choice-active" : "review-choice"}>Resume In Progress</button>
                  </div>
                  {task.status === "in_review" && (
                    <button
                      onClick={approve}
                      disabled={!canMarkDone}
                      title={canMarkDone ? "Approve this task as Done." : doneGateReason}
                      className="primary-action disabled:opacity-40"
                    >
                      <CheckCircle2 size={16} /> Mark Done
                    </button>
                  )}
                  {task.status === "in_review" && !canMarkDone && (
                    <p className="rounded bg-amber-50 px-2 py-1.5 text-xs text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
                      {doneGateReason}
                    </p>
                  )}
                  <button onClick={flagRevision} disabled={!whatToReview.trim()} className="secondary-action disabled:opacity-40"><RotateCcw size={16} /> Request Revision</button>
                  {task.status === "done" && task.review_state === "approved" && (
                    <button
                      onClick={sendReport}
                      disabled={!canSendToReport}
                      title={canSendToReport ? "Send accepted evidence to Reports." : reportGateReason}
                      className="secondary-action disabled:opacity-40"
                    >
                      <Send size={16} /> Send to Report
                    </button>
                  )}
                  {task.status === "done" && task.review_state === "approved" && !canSendToReport && (
                    <p className="rounded bg-amber-50 px-2 py-1.5 text-xs text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
                      {reportGateReason}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-500">Review actions are available once agents place the task in review.</p>
              )}
              {requiresWhatToReview && <p className="mt-2 text-xs text-slate-500">What to Review becomes the next agent instruction and telemetry signal.</p>}
            </section>

            <section className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <h4 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">Quality</h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <Metric label="Review cycles" value={quality?.review_cycle_count ?? task.review_cycle_count} />
                <Metric label="Failure streak" value={quality?.failure_streak ?? task.failure_streak} />
                <Metric label="Human score" value={task.human_feedback_score == null ? "N/A" : `${Math.round(task.human_feedback_score * 100)}%`} />
                <Metric label="Consensus" value={task.consensus_score == null ? "N/A" : `${Math.round(task.consensus_score * 100)}%`} />
              </div>
              {task.review_failure_category && <p className="mt-3 text-xs text-slate-500">Last issue: {task.review_failure_category.replace(/_/g, " ")}</p>}
            </section>

            <section className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <h4 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-slate-900 dark:text-white">
                {researchValidityReady ? <ShieldCheck size={14} className="text-emerald-500" /> : <AlertTriangle size={14} className="text-amber-500" />}
                Research Validity
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <Metric label="Coding runs" value={researchValidityState?.coding_run_count ?? 0} />
                <Metric label="Accepted codes" value={`${acceptedCodeApplicationCount}/${codeApplicationCount}`} />
              </div>
              <div className="mt-3 rounded bg-slate-50 p-2 text-xs dark:bg-slate-800">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500">Latest gate</span>
                  <span className={researchValidityReady ? "font-medium text-emerald-700 dark:text-emerald-300" : "font-medium text-amber-700 dark:text-amber-300"}>
                    {(needsCodingBeforeReport ? "coding required" : latestPromotionStatus).replace(/_/g, " ")}
                  </span>
                </div>
                {latestReliabilityMethod && (
                  <p className="mt-1 truncate text-slate-500">{latestReliabilityMethod}</p>
                )}
              </div>
              {blockedReviewItems.length > 0 && (
                <div className="mt-3 space-y-1.5">
                  {blockedReviewItems.slice(0, 3).map((item) => (
                    <div key={item.id} className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-200">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate">{item.code_id}</span>
                        <span className="shrink-0">{item.promotion_status.replace(/_/g, " ")}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-700 dark:bg-slate-800/80">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-200">
                    <Network size={13} aria-hidden="true" />
                    Evidence Graph
                  </div>
                  <span className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
                    {traceabilityLoading ? "Loading" : traceability?.retrieval_mode || "No trace"}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Metric label="Low-agreement deps" value={traceLowAgreementCount} />
                  <Metric label="Reconciliations" value={traceReconciliationCount} />
                  <Metric label="Report links" value={traceReportDependencyCount} />
                  <Metric label="Graph edges" value={traceEdgeCount} />
                </div>
                {traceLowAgreementCount > 0 && (
                  <p className="mt-2 text-[11px] font-medium text-amber-700 dark:text-amber-300">
                    Resolve or reject low-agreement evidence before this task can safely feed reporting.
                  </p>
                )}
                {traceability?.contract?.promotion_rule && (
                  <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
                    {traceability.contract.promotion_rule.replace(/_/g, " ")}
                  </p>
                )}
              </div>
              {codingRunError && <p className="mt-2 text-xs text-red-600 dark:text-red-300">{codingRunError}</p>}
              <button onClick={startCodingRun} disabled={codingRunLoading || !hasActiveTaskProject} className="secondary-action mt-3 disabled:opacity-40">
                <ShieldCheck size={16} /> {codingRunLoading ? "Coding..." : "Start Coding Run"}
              </button>
            </section>

            <section className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <h4 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">Atomic Path</h4>
              <div className="space-y-2 text-xs">
                {(["documents", "nuggets", "facts", "insights", "recommendations", "reports"] as const).map((key) => (
                  <div key={key} className="rounded bg-slate-50 p-2 dark:bg-slate-800">
                    <div className="flex items-center justify-between font-medium capitalize text-slate-700 dark:text-slate-200"><span>{key}</span><span>{atomicPath?.[key]?.count ?? 0}</span></div>
                    {(atomicPath?.[key]?.items || []).slice(0, 2).map((item: any) => <p key={item.id} className="mt-1 truncate text-slate-500">{item.title || item.text || item.id}</p>)}
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </div>

        <div className="sticky bottom-0 flex items-center justify-end gap-2 border-t border-slate-200 bg-white px-5 py-3 dark:border-slate-700 dark:bg-slate-900">
          {saveError && <p role="alert" className="mr-auto text-xs text-red-600 dark:text-red-400">{saveError}</p>}
          <button onClick={() => void saveDraft()} disabled={saving || !title.trim() || !hasActiveTaskProject} className="secondary-action disabled:opacity-40"><Save size={15} /> Save</button>
          <button onClick={closeWithSave} disabled={saving || !title.trim() || !hasActiveTaskProject} className="primary-action disabled:opacity-40">Done Editing</button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, icon, children }: { label: string; icon?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-center gap-1 text-xs font-medium text-slate-500">{icon}{label}</span>
      {children}
    </label>
  );
}

function IconButton({ children, onClick, label }: { children: ReactNode; onClick: () => void; label: string }) {
  return <button type="button" onClick={onClick} className="rounded-lg bg-slate-100 p-2 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300" aria-label={label} title={label}>{children}</button>;
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded bg-slate-50 p-2 dark:bg-slate-800"><p className="text-slate-500">{label}</p><p className="mt-1 font-semibold text-slate-900 dark:text-white">{value}</p></div>;
}

function DocumentSection({ title, icon, docs, getDocTitle, onRemove, onPick, picker }: { title: string; icon: ReactNode; docs: string[]; getDocTitle: (id: string) => string; onRemove: (id: string) => void; onPick: () => void; picker: ReactNode }) {
  return (
    <Field label={title} icon={icon}>
      <div className="space-y-2">
        {docs.map((docId) => (
          <div key={docId} className="flex items-center gap-2 rounded bg-slate-50 px-2 py-1 text-xs dark:bg-slate-800">
            <span className="min-w-0 flex-1 truncate">{getDocTitle(docId)}</span>
            <IconButton onClick={() => onRemove(docId)} label="Remove document"><X size={13} /></IconButton>
          </div>
        ))}
        <div className="relative">
          <button type="button" onClick={onPick} className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"><Plus size={12} /> Attach</button>
          {picker}
        </div>
      </div>
    </Field>
  );
}

const DocumentPickerDropdown = forwardRef<HTMLDivElement, { documents: { id: string; title: string }[]; loading: boolean; excludeIds: string[]; onSelect: (id: string) => void }>(function DocumentPickerDropdown({ documents, loading, excludeIds, onSelect }, ref) {
  const available = documents.filter((d) => !excludeIds.includes(d.id));
  return (
    <div ref={ref} className="absolute left-0 top-8 z-50 max-h-56 w-80 overflow-y-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-800">
      {loading ? <p className="px-3 py-2 text-xs text-slate-400">Loading documents...</p> : available.length === 0 ? <p className="px-3 py-2 text-xs text-slate-400">No available documents.</p> : available.map((doc) => (
        <button key={doc.id} onClick={() => onSelect(doc.id)} className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-slate-50 dark:hover:bg-slate-700">
          <FileText size={12} className="shrink-0 text-slate-400" />
          <span className="truncate text-slate-700 dark:text-slate-300">{doc.title}</span>
        </button>
      ))}
    </div>
  );
});
