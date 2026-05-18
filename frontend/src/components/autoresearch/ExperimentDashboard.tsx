"use client";

import { useEffect, useState } from "react";
import {
  FlaskConical,
  CheckCircle2,
  TrendingUp,
  Activity,
  Play,
  Square,
  Loader2,
  ClipboardCheck,
  Cpu,
  RotateCcw,
  Bot,
  Database,
  Radio,
  Gauge,
} from "lucide-react";
import { useAutoresearchStore } from "@/stores/autoresearchStore";
import { useProjectStore } from "@/stores/projectStore";
import { cn, formatDate } from "@/lib/utils";
import type { AutoresearchLoopType } from "@/lib/types";

const LOOP_TYPES: { value: AutoresearchLoopType; label: string }[] = [
  { value: "skill_prompt", label: "Skill Prompt" },
  { value: "model_temp", label: "Model Temp" },
  { value: "rag_params", label: "RAG Params" },
  { value: "persona", label: "Persona" },
  { value: "question_bank", label: "Question Bank" },
  { value: "ui_sim", label: "UI Sim" },
];

export default function ExperimentDashboard() {
  const { status, experiments, fetchStatus, fetchExperiments, startLoop, stopLoop, error } =
    useAutoresearchStore();
  const { activeProjectId } = useProjectStore();

  const [loopType, setLoopType] = useState<string>("model_temp");
  const [target, setTarget] = useState("");
  const [maxIterations, setMaxIterations] = useState(20);

  useEffect(() => {
    fetchStatus(activeProjectId);
    fetchExperiments({ project_id: activeProjectId, limit: 20 });
  }, [activeProjectId, fetchStatus, fetchExperiments]);

  // Refresh status periodically when a loop is running
  useEffect(() => {
    if (!status?.running) return;
    const interval = setInterval(() => {
      fetchStatus(activeProjectId);
      fetchExperiments({ project_id: activeProjectId, limit: 20 });
    }, 5000);
    return () => clearInterval(interval);
  }, [activeProjectId, status?.running, fetchStatus, fetchExperiments]);

  const totalExperiments = experiments.length;
  const keptCount = experiments.filter((e) => e.kept).length;
  const successRate = totalExperiments > 0 ? Math.round((keptCount / totalExperiments) * 100) : 0;
  const bestDelta = experiments.length > 0
    ? Math.max(...experiments.filter((e) => e.kept).map((e) => e.delta), 0)
    : 0;
  const taskMetrics = status?.operational_metrics?.tasks;
  const computeMetrics = status?.operational_metrics?.compute_pool;
  const agentMetrics = status?.operational_metrics?.agents;
  const pipelineMetrics = status?.operational_metrics?.research_pipeline;
  const telemetryMetrics = status?.operational_metrics?.telemetry;
  const loopMetrics = status?.operational_metrics?.loops;
  const collectionMetrics = status?.operational_metrics?.research_collection;

  const handleStart = () => {
    if (!activeProjectId || !target.trim()) return;
    startLoop({
      loop_type: loopType,
      target: target.trim(),
      max_iterations: maxIterations,
      project_id: activeProjectId,
    });
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Active experiment card */}
      {status?.running && status.current_experiment && (
        <div className="rounded-lg border border-istara-300 dark:border-istara-700 bg-istara-50 dark:bg-istara-900/20 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Loader2 size={18} className="animate-spin text-istara-600 dark:text-istara-400" />
              <h3 className="font-semibold text-istara-700 dark:text-istara-400">
                Experiment Running
              </h3>
            </div>
            <button
              onClick={() => stopLoop(activeProjectId)}
              aria-label="Stop experiment loop"
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
            >
              <Square size={14} />
              Stop
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <span className="text-slate-500 dark:text-slate-400">Loop Type</span>
              <p className="font-medium text-slate-900 dark:text-white">
                {status.current_experiment.loop_type}
              </p>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Target</span>
              <p className="font-medium text-slate-900 dark:text-white">
                {status.current_experiment.target_name}
              </p>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Hypothesis</span>
              <p className="font-medium text-slate-900 dark:text-white truncate">
                {status.current_experiment.hypothesis}
              </p>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Baseline</span>
              <p className="font-medium text-slate-900 dark:text-white">
                {status.current_experiment.baseline_score.toFixed(3)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <FlaskConical size={16} />
            <span className="text-xs font-medium uppercase">Total Experiments</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{totalExperiments}</p>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <CheckCircle2 size={16} />
            <span className="text-xs font-medium uppercase">Kept Improvements</span>
          </div>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">{keptCount}</p>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <TrendingUp size={16} />
            <span className="text-xs font-medium uppercase">Success Rate</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{successRate}%</p>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <Activity size={16} />
            <span className="text-xs font-medium uppercase">Best Delta</span>
          </div>
          <p className="text-2xl font-bold text-istara-600 dark:text-istara-400">
            +{bestDelta.toFixed(3)}
          </p>
        </div>
      </div>

      {/* Branch integration signals */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200 mb-4">
            <ClipboardCheck size={18} className="text-istara-600 dark:text-istara-400" />
            <h3 className="font-semibold">Task Review Signals</h3>
          </div>
          {taskMetrics ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <MiniMetric label="Tasks" value={taskMetrics.total} />
                <MiniMetric label="In Review" value={taskMetrics.in_review} />
                <MiniMetric label="Approved" value={taskMetrics.approved} />
                <MiniMetric label="Needs Revision" value={taskMetrics.needs_revision} tone={taskMetrics.needs_revision > 0 ? "amber" : "slate"} />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <ProgressMetric label="Completion" value={taskMetrics.completion_rate} />
                <ProgressMetric label="Approval Rate" value={taskMetrics.approval_rate} />
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                  <RotateCcw size={12} />
                  {taskMetrics.review_cycles} review cycles
                </span>
                <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                  {taskMetrics.review_events} review events
                </span>
                <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                  {taskMetrics.approval_events} approvals
                </span>
                <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                  {taskMetrics.validation_runs} validations
                </span>
                <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                  Validation success {taskMetrics.validation_success_rate.toFixed(1)}%
                </span>
                {taskMetrics.avg_human_feedback !== null && (
                  <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                    Human feedback {taskMetrics.avg_human_feedback.toFixed(2)}
                  </span>
                )}
                {taskMetrics.avg_consensus !== null && (
                  <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                    Consensus {taskMetrics.avg_consensus.toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Task review metrics are not available from this backend.
            </p>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200 mb-4">
            <Cpu size={18} className="text-istara-600 dark:text-istara-400" />
            <h3 className="font-semibold">Compute Pool Availability</h3>
          </div>
          {computeMetrics ? (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <MiniMetric label="Nodes" value={computeMetrics.total_nodes} />
                <MiniMetric label="Alive" value={computeMetrics.alive_nodes} tone={computeMetrics.alive_nodes > 0 ? "green" : "amber"} />
                <MiniMetric label="Models" value={computeMetrics.available_model_count} />
              </div>
              {computeMetrics.available_models.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {computeMetrics.available_models.slice(0, 8).map((model) => (
                    <span
                      key={model}
                      className="max-w-full truncate rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1 text-xs text-slate-600 dark:text-slate-300"
                    >
                      {model}
                    </span>
                  ))}
                  {computeMetrics.available_models.length > 8 && (
                    <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1 text-xs text-slate-500">
                      +{computeMetrics.available_models.length - 8} more
                    </span>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-400 dark:text-slate-500">
                  No healthy LLM models are currently advertised by the compute pool.
                </p>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Compute pool metrics are not available from this backend.
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200 mb-4">
            <Gauge size={18} className="text-istara-600 dark:text-istara-400" />
            <h3 className="font-semibold">Telemetry & Model Health</h3>
          </div>
          {telemetryMetrics ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <MiniMetric label="24h Spans" value={telemetryMetrics.spans_last_24h} />
                <MiniMetric label="24h Errors" value={telemetryMetrics.errors_last_24h} tone={telemetryMetrics.errors_last_24h > 0 ? "amber" : "slate"} />
                <MiniMetric label="Models" value={telemetryMetrics.model_entries} />
                <MiniMetric label="AR Models" value={telemetryMetrics.autoresearch_model_entries} />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <ProgressMetric label="24h Error Rate" value={telemetryMetrics.error_rate_24h} inverse />
                <ProgressMetric label="Best Model Quality" value={(telemetryMetrics.best_model_quality ?? 0) * 100} />
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                  Telemetry {telemetryMetrics.enabled ? "enabled" : "disabled"}
                </span>
                {telemetryMetrics.avg_quality_24h !== null && (
                  <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                    24h quality {telemetryMetrics.avg_quality_24h.toFixed(2)}
                  </span>
                )}
                {telemetryMetrics.avg_model_quality !== null && (
                  <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                    Avg model quality {telemetryMetrics.avg_model_quality.toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Telemetry metrics are not available from this backend.
            </p>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200 mb-4">
            <Bot size={18} className="text-istara-600 dark:text-istara-400" />
            <h3 className="font-semibold">Agent & Loop Health</h3>
          </div>
          {agentMetrics && loopMetrics ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <MiniMetric label="Agents" value={agentMetrics.total} />
                <MiniMetric label="Working" value={agentMetrics.working} />
                <MiniMetric label="Unhealthy" value={agentMetrics.unhealthy_heartbeats} tone={agentMetrics.unhealthy_heartbeats > 0 ? "amber" : "slate"} />
                <MiniMetric label="Schedules" value={loopMetrics.active_schedules} />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <ProgressMetric label="Agent Error Rate" value={agentMetrics.error_rate} inverse />
                <ProgressMetric label="Active Schedules" value={loopMetrics.total_schedules ? (loopMetrics.active_schedules / loopMetrics.total_schedules) * 100 : 0} />
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                  {agentMetrics.executions} agent executions
                </span>
                <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                  {loopMetrics.schedule_executions} schedule runs
                </span>
                {loopMetrics.running_schedules > 0 && (
                  <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                    {loopMetrics.running_schedules} running now
                  </span>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Agent and loop metrics are not available from this backend.
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200 mb-4">
            <Database size={18} className="text-istara-600 dark:text-istara-400" />
            <h3 className="font-semibold">Research Pipeline Coverage</h3>
          </div>
          {pipelineMetrics ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <MiniMetric label="Documents" value={pipelineMetrics.documents} />
                <MiniMetric label="Indexed" value={pipelineMetrics.indexed_text_documents} />
                <MiniMetric label="Findings" value={pipelineMetrics.findings} />
                <MiniMetric label="Code Reviews" value={pipelineMetrics.pending_code_reviews} tone={pipelineMetrics.pending_code_reviews > 0 ? "amber" : "slate"} />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <ProgressMetric label="Document Ready Rate" value={pipelineMetrics.documents ? (pipelineMetrics.ready_documents / pipelineMetrics.documents) * 100 : 0} />
                <ProgressMetric label="Code Approval Rate" value={pipelineMetrics.code_applications ? (pipelineMetrics.approved_code_reviews / pipelineMetrics.code_applications) * 100 : 0} />
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                  {pipelineMetrics.errored_documents} document errors
                </span>
                {pipelineMetrics.avg_insight_confidence !== null && (
                  <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                    Insight confidence {pipelineMetrics.avg_insight_confidence.toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Research pipeline metrics are not available from this backend.
            </p>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200 mb-4">
            <Radio size={18} className="text-istara-600 dark:text-istara-400" />
            <h3 className="font-semibold">Research Collection</h3>
          </div>
          {collectionMetrics ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <MiniMetric label="Deployments" value={collectionMetrics.deployments} />
                <MiniMetric label="Active" value={collectionMetrics.active_deployments} />
                <MiniMetric label="Responses" value={collectionMetrics.deployment_responses + collectionMetrics.survey_responses} />
                <MiniMetric label="Survey Links" value={collectionMetrics.survey_links} />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <ProgressMetric label="Deployment Completion" value={collectionMetrics.deployment_completion_rate} />
                <ProgressMetric label="Active Integrations" value={collectionMetrics.survey_integrations ? (collectionMetrics.active_survey_integrations / collectionMetrics.survey_integrations) * 100 : 0} />
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                  Target {collectionMetrics.deployment_targets} deployment responses
                </span>
                <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-1">
                  {collectionMetrics.survey_integrations} survey integrations
                </span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Research collection metrics are not available from this backend.
            </p>
          )}
        </div>
      </div>

      {/* Start new loop */}
      {!status?.running && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
            Start Experiment Loop
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label
                htmlFor="ar-loop-type"
                className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1"
              >
                Loop Type
              </label>
              <select
                id="ar-loop-type"
                value={loopType}
                onChange={(e) => setLoopType(e.target.value)}
                aria-label="Experiment loop type"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-istara-500"
              >
                {LOOP_TYPES.map((lt) => (
                  <option key={lt.value} value={lt.value}>
                    {lt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="ar-target"
                className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1"
              >
                Target
              </label>
              <input
                id="ar-target"
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="skill name, agent id..."
                aria-label="Experiment target"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-istara-500"
              />
            </div>
            <div>
              <label
                htmlFor="ar-max-iter"
                className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1"
              >
                Max Iterations
              </label>
              <input
                id="ar-max-iter"
                type="number"
                value={maxIterations}
                onChange={(e) => setMaxIterations(Number(e.target.value))}
                min={1}
                max={200}
                aria-label="Maximum iterations"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-istara-500"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleStart}
                disabled={!activeProjectId || !target.trim() || !status?.enabled}
                aria-label="Start experiment loop"
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors w-full justify-center",
                  activeProjectId && target.trim() && status?.enabled
                    ? "bg-istara-600 text-white hover:bg-istara-700"
                    : "bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed"
                )}
              >
                <Play size={14} />
                Start
              </button>
            </div>
          </div>
          {!status?.enabled && (
            <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
              Autoresearch is disabled. Enable it in the Config tab first.
            </p>
          )}
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="rounded-lg border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Recent experiments timeline */}
      <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
          Recent Experiments
        </h3>
        {experiments.length === 0 ? (
          <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-8">
            No experiments yet. Start a loop to begin self-improvement.
          </p>
        ) : (
          <div className="space-y-2">
            {experiments.slice(0, 15).map((exp) => (
              <div
                key={exp.id}
                className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
              >
                {/* Status indicator */}
                <div
                  className={cn(
                    "w-2.5 h-2.5 rounded-full shrink-0",
                    exp.status === "running"
                      ? "bg-blue-500 animate-pulse"
                      : exp.kept
                        ? "bg-green-500"
                        : exp.status === "failed"
                          ? "bg-red-500"
                          : "bg-slate-300 dark:bg-slate-600"
                  )}
                  aria-label={exp.kept ? "Kept" : exp.status === "failed" ? "Failed" : "Discarded"}
                />

                {/* Loop type badge */}
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                  {exp.loop_type}
                </span>

                {/* Target */}
                <span className="text-sm text-slate-700 dark:text-slate-300 truncate min-w-0">
                  {exp.target_name}
                </span>

                {/* Hypothesis (truncated) */}
                <span className="text-xs text-slate-400 dark:text-slate-500 truncate hidden md:block flex-1 min-w-0">
                  {exp.hypothesis}
                </span>

                {/* Score delta */}
                <span
                  className={cn(
                    "text-sm font-mono whitespace-nowrap",
                    exp.delta > 0
                      ? "text-green-600 dark:text-green-400"
                      : exp.delta < 0
                        ? "text-red-600 dark:text-red-400"
                        : "text-slate-400"
                  )}
                >
                  {exp.delta > 0 ? "+" : ""}
                  {exp.delta.toFixed(3)}
                </span>

                {/* Timestamp */}
                <span className="text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap hidden lg:block">
                  {exp.started_at ? formatDate(exp.started_at) : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MiniMetric({
  label,
  value,
  tone = "slate",
}: {
  label: string;
  value: number | string;
  tone?: "slate" | "green" | "amber";
}) {
  const toneClass =
    tone === "green"
      ? "text-green-600 dark:text-green-400"
      : tone === "amber"
        ? "text-amber-600 dark:text-amber-400"
        : "text-slate-900 dark:text-white";

  return (
    <div className="rounded-lg bg-slate-50 dark:bg-slate-800/50 px-3 py-2">
      <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
      <p className={cn("text-xl font-bold", toneClass)}>{value}</p>
    </div>
  );
}

function ProgressMetric({ label, value, inverse = false }: { label: string; value: number; inverse?: boolean }) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const barColor = inverse
    ? clamped > 20
      ? "bg-red-500"
      : clamped > 5
        ? "bg-amber-500"
        : "bg-green-500"
    : "bg-istara-500";

  return (
    <div>
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
        <span>{label}</span>
        <span>{clamped.toFixed(1)}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div
          className={cn("h-full rounded-full transition-all duration-500", barColor)}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
