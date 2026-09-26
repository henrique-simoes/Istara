"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Database, Loader2, RefreshCw } from "lucide-react";
import {
  settings as settingsApi,
  type EmbeddingMigration,
  type EmbeddingProfile,
} from "@/lib/api";
import { cn } from "@/lib/utils";

/** Embedders with published query/document prompts that Istara applies (embedding_prompts.py). */
const SUGGESTED_MODELS = [
  { model: "embeddinggemma", note: "Google EmbeddingGemma 300M, 100+ languages" },
  { model: "qwen3-embedding:0.6b", note: "Qwen3-Embedding 0.6B, 100+ languages" },
  { model: "bge-m3", note: "BGE-M3, 100+ languages" },
  { model: "nomic-embed-text", note: "nomic-embed-text, English" },
];

const POLL_MS = 1500;

export function schemeLabel(scheme: string): string {
  return scheme === "raw" ? "raw text (no prompts)" : `${scheme} prompts`;
}

/** The status line for a migration, or null when there is nothing to say. */
export function migrationSummary(
  migration: EmbeddingMigration | null
): { tone: "progress" | "done" | "failed"; text: string } | null {
  if (!migration) return null;
  if (migration.state === "running") {
    return {
      tone: "progress",
      text: `Re-indexing with ${migration.model_id}: ${migration.stores_done ?? 0} of ${
        migration.stores_total ?? "…"
      } tables, ${migration.rows_reembedded ?? 0} chunks re-embedded.`,
    };
  }
  if (migration.state === "done") {
    return {
      tone: "done",
      text: `Now using ${migration.model_id}: ${migration.stores_done ?? 0} tables re-embedded (${
        migration.rows_reembedded ?? 0
      } chunks), ${migration.stores_skipped ?? 0} already current.`,
    };
  }
  if (migration.state === "failed") {
    return {
      tone: "failed",
      text: `The re-index stopped: ${migration.error}. Run it again to continue with the tables left.`,
    };
  }
  return null;
}

/** A start error in the researcher's terms; nothing changes when the model cannot embed. */
export function explainStartError(message: string): string {
  if (message.startsWith("embedding_model_unavailable")) {
    return `That model could not embed, so nothing changed (${message}).`;
  }
  if (message === "migration_already_running") {
    return "A re-index is already running; wait for it to finish.";
  }
  return message;
}

/**
 * The install's embedding model, and (for administrators) a governed switch to another one: the
 * model is checked first, a new embedding-profile version becomes active, and every project's
 * stored chunks are re-embedded so the two vector spaces never mix. Keyword search is unaffected.
 */
export default function EmbeddingModelSection() {
  const [profile, setProfile] = useState<EmbeddingProfile | null>(null);
  const [migration, setMigration] = useState<EmbeddingMigration | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [modelId, setModelId] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    setLoadError("");
    try {
      const status = await settingsApi.embeddingProfile();
      setProfile(status.active);
      setMigration(status.migration);
      return status;
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Could not load the embedding model.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const poll = useCallback(async () => {
    const status = await load();
    if (status?.migration.state === "running") {
      timer.current = setTimeout(poll, POLL_MS);
    }
  }, [load]);

  useEffect(() => {
    void poll();
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [poll]);

  useEffect(() => {
    if (confirming) confirmRef.current?.focus();
  }, [confirming]);

  const running = migration?.state === "running";
  const summary = migrationSummary(migration);
  const target = modelId.trim();

  async function startMigration() {
    setSubmitting(true);
    setSubmitError("");
    try {
      const status = await settingsApi.startEmbeddingMigration(target);
      setMigration(status.migration);
      setConfirming(false);
      timer.current = setTimeout(poll, POLL_MS);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "The migration could not start.");
      setConfirming(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section
      aria-labelledby="embedding-model-heading"
      className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5"
      data-testid="embedding-model-section"
    >
      <h3
        id="embedding-model-heading"
        className="font-medium text-slate-900 dark:text-white mb-1 flex items-center gap-2"
      >
        <Database size={18} aria-hidden="true" /> Embedding model
      </h3>
      <p className="text-sm text-slate-600 dark:text-slate-300 mb-4">
        The model that turns documents and questions into vectors for semantic search. Changing it
        re-embeds every project&apos;s stored chunks; keyword search keeps working throughout.
      </p>

      {loading ? (
        <p className="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-2" role="status">
          <Loader2 size={14} className="animate-spin" aria-hidden="true" /> Loading the embedding
          model…
        </p>
      ) : loadError ? (
        <div className="rounded-lg border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 p-3 text-sm text-red-800 dark:text-red-200" role="alert">
          <p className="flex items-center gap-2">
            <AlertTriangle size={14} aria-hidden="true" /> {loadError}
          </p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              void poll();
            }}
            className="mt-2 inline-flex items-center gap-1 rounded-md border border-red-300 dark:border-red-800 px-3 py-1.5 text-sm font-medium hover:bg-red-100 dark:hover:bg-red-900/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-istara-500"
          >
            <RefreshCw size={14} aria-hidden="true" /> Retry
          </button>
        </div>
      ) : profile ? (
        <>
          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm mb-4">
            <div>
              <dt className="text-slate-600 dark:text-slate-300">Active model</dt>
              <dd className="font-mono text-slate-900 dark:text-white break-all" data-testid="embedding-active-model">
                {profile.model_id}
              </dd>
            </div>
            <div>
              <dt className="text-slate-600 dark:text-slate-300">Prompts</dt>
              <dd className="text-slate-900 dark:text-white">{schemeLabel(profile.prompt_scheme)}</dd>
            </div>
            <div>
              <dt className="text-slate-600 dark:text-slate-300">Profile version</dt>
              <dd className="text-slate-900 dark:text-white">
                v{profile.version}
                {profile.dimension ? ` · ${profile.dimension} dimensions` : ""}
              </dd>
            </div>
          </dl>

          <div role="status" aria-live="polite" data-testid="embedding-migration-status">
            {summary && (
              <p
                className={cn(
                  "flex items-start gap-2 text-sm mb-3",
                  summary.tone === "progress" && "text-slate-700 dark:text-slate-200",
                  summary.tone === "done" && "text-green-700 dark:text-green-300",
                  summary.tone === "failed" && "text-red-700 dark:text-red-300"
                )}
              >
                {summary.tone === "progress" && (
                  <Loader2 size={14} className="mt-0.5 shrink-0 animate-spin" aria-hidden="true" />
                )}
                {summary.tone === "done" && (
                  <CheckCircle2 size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
                )}
                {summary.tone === "failed" && (
                  <AlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
                )}
                {summary.text}
              </p>
            )}
          </div>

          <form
            className="flex flex-col sm:flex-row sm:items-end gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              if (target && !running) setConfirming(true);
            }}
          >
            <div className="flex-1 min-w-0">
              <label htmlFor="embedding-model-input" className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
                Switch to model
              </label>
              <input
                id="embedding-model-input"
                list="embedding-model-suggestions"
                value={modelId}
                onChange={(event) => {
                  setModelId(event.target.value);
                  setSubmitError("");
                  setConfirming(false);
                }}
                placeholder="e.g. embeddinggemma"
                disabled={running}
                aria-describedby="embedding-model-hint"
                className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm font-mono text-slate-900 dark:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-istara-500"
              />
              <datalist id="embedding-model-suggestions">
                {SUGGESTED_MODELS.map((item) => (
                  <option key={item.model} value={item.model}>
                    {item.note}
                  </option>
                ))}
              </datalist>
              <p id="embedding-model-hint" className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                The model must already be served by your embedding provider (for example{" "}
                <code>ollama pull embeddinggemma</code>). Istara checks it before changing anything.
              </p>
            </div>
            <button
              type="submit"
              disabled={!target || running || submitting}
              className={cn(
                "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium min-h-[40px]",
                "bg-istara-600 text-white hover:bg-istara-700 disabled:opacity-50 disabled:cursor-not-allowed",
                "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-istara-500"
              )}
            >
              <RefreshCw size={14} aria-hidden="true" /> Re-index with this model
            </button>
          </form>

          {confirming && (
            <div
              role="alertdialog"
              aria-labelledby="embedding-confirm-title"
              aria-describedby="embedding-confirm-body"
              className="mt-3 rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40 p-3 text-sm"
            >
              <p id="embedding-confirm-title" className="font-medium text-amber-900 dark:text-amber-100">
                Re-embed every project with {target}?
              </p>
              <p id="embedding-confirm-body" className="text-amber-900 dark:text-amber-100 mt-1">
                Semantic search pauses per project while its chunks are re-embedded. Nothing is
                deleted, and the previous profile version stays on record.
              </p>
              <div className="mt-3 flex gap-2">
                <button
                  ref={confirmRef}
                  type="button"
                  onClick={() => void startMigration()}
                  disabled={submitting}
                  className="rounded-md bg-amber-700 px-3 py-1.5 font-medium text-white hover:bg-amber-800 disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-amber-600"
                >
                  {submitting ? "Checking the model…" : "Re-embed now"}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirming(false)}
                  className="rounded-md border border-amber-400 dark:border-amber-700 px-3 py-1.5 font-medium text-amber-900 dark:text-amber-100 hover:bg-amber-100 dark:hover:bg-amber-900/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-600"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {submitError && (
            <p className="mt-3 flex items-start gap-2 text-sm text-red-700 dark:text-red-300" role="alert" data-testid="embedding-migration-error">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
              {explainStartError(submitError)}
            </p>
          )}
        </>
      ) : null}
    </section>
  );
}
