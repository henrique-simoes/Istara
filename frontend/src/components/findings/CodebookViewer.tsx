"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Book,
  ChevronDown,
  ChevronRight,
  Tag,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { codebookVersions as codebookApi } from "@/lib/api";
import type { CodebookVersionType, CodeEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

interface CodebookViewerProps {
  projectId: string;
}

const METHODOLOGY_LABELS: Record<string, string> = {
  reflexive_ta: "Reflexive TA",
  codebook_ta: "Codebook TA",
  grounded_theory: "Grounded Theory",
};

const METHODOLOGY_COLORS: Record<string, string> = {
  reflexive_ta:
    "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400",
  codebook_ta:
    "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
  grounded_theory:
    "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400",
};

const CODE_FIELDS: {
  key: keyof CodeEntry;
  label: string;
}[] = [
  { key: "brief_definition", label: "Brief Definition" },
  { key: "full_definition", label: "Full Definition" },
  { key: "exclusion_criteria", label: "Exclusion Criteria" },
  { key: "typical_example", label: "Typical Example" },
  { key: "boundary_example", label: "Boundary Example" },
];

export default function CodebookViewer({ projectId }: CodebookViewerProps) {
  const [versions, setVersions] = useState<CodebookVersionType[]>([]);
  const [selectedVersion, setSelectedVersion] =
    useState<CodebookVersionType | null>(null);
  const [expandedCodes, setExpandedCodes] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadVersions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await codebookApi.list(projectId);
      setVersions(data);
      if (data.length > 0) {
        setSelectedVersion(data[0]);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load codebook versions"
      );
    }
    setLoading(false);
  }, [projectId]);

  useEffect(() => {
    loadVersions();
  }, [loadVersions]);

  const toggleCode = (codeId: string) => {
    setExpandedCodes((prev) => {
      const next = new Set(prev);
      if (next.has(codeId)) {
        next.delete(codeId);
      } else {
        next.add(codeId);
      }
      return next;
    });
  };

  const handleVersionChange = (versionId: string) => {
    const version = versions.find((v) => v.id === versionId);
    if (version) {
      setSelectedVersion(version);
      setExpandedCodes(new Set());
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto" role="status" aria-live="polite" aria-label="Loading codebook">
        <span className="sr-only">Loading codebook...</span>
        <div className="p-4 border-b border-slate-200 dark:border-slate-800">
          <div className="h-6 w-48 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
        </div>
        <div className="p-4 space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="border border-slate-200 dark:border-slate-700 rounded-lg p-4"
            >
              <div className="h-4 w-32 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-2" />
              <div className="h-3 w-64 bg-slate-100 dark:bg-slate-800 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-8" role="alert">
        <div className="text-center">
          <AlertCircle
            size={32}
            className="mx-auto text-red-500 dark:text-red-400 mb-3"
            aria-hidden="true"
          />
          <p className="text-sm text-red-600 dark:text-red-400 font-medium mb-1">
            Failed to load codebook
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
            {error}
          </p>
          <button
            onClick={loadVersions}
            aria-label="Retry loading codebook"
            className="text-xs px-3 py-1.5 rounded-md bg-reclaw-600 text-white hover:bg-reclaw-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-reclaw-500 focus-visible:ring-offset-1"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (versions.length === 0 || !selectedVersion) {
    return (
      <div className="flex-1 flex items-center justify-center p-8" role="status">
        <div className="text-center">
          <Book
            size={32}
            className="mx-auto text-slate-300 dark:text-slate-600 mb-3"
            aria-hidden="true"
          />
          <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
            No codebook yet
          </p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
            Run a thematic analysis to generate one
          </p>
        </div>
      </div>
    );
  }

  const codes: CodeEntry[] = selectedVersion.codes || [];

  return (
    <div className="flex-1 overflow-y-auto" role="region" aria-label="Codebook viewer">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Book size={18} className="text-reclaw-600 dark:text-reclaw-400" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Codebook v{selectedVersion.version}
            </h2>
            <span
              className={cn(
                "text-xs font-medium px-2 py-0.5 rounded-full",
                METHODOLOGY_COLORS[selectedVersion.methodology] ||
                  "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
              )}
            >
              {METHODOLOGY_LABELS[selectedVersion.methodology] ||
                selectedVersion.methodology}
            </span>
          </div>

          {/* Version selector */}
          {versions.length > 1 && (
            <div>
              <label htmlFor="codebook-version-select" className="sr-only">
                Select codebook version
              </label>
              <select
                id="codebook-version-select"
                value={selectedVersion.id}
                onChange={(e) => handleVersionChange(e.target.value)}
                className="text-sm border border-slate-200 dark:border-slate-700 rounded-md px-2 py-1 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              >
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {selectedVersion.change_log && (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {selectedVersion.change_log}
          </p>
        )}

        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
          {codes.length} code{codes.length !== 1 ? "s" : ""} defined
        </p>
      </div>

      {/* Code list */}
      <div className="p-4 space-y-2" role="list" aria-label="Codebook entries">
        {codes.map((code) => {
          const isExpanded = expandedCodes.has(code.code_id);
          const panelId = `code-panel-${code.code_id}`;
          return (
            <div
              key={code.code_id}
              role="listitem"
              className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden"
            >
              {/* Code header (expandable) */}
              <button
                onClick={() => toggleCode(code.code_id)}
                aria-expanded={isExpanded}
                aria-controls={panelId}
                aria-label={`${isExpanded ? "Collapse" : "Expand"} code: ${code.label}`}
                className="flex items-center justify-between w-full p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-reclaw-500 focus-visible:ring-inset"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {isExpanded ? (
                    <ChevronDown
                      size={16}
                      className="text-slate-400 shrink-0"
                      aria-hidden="true"
                    />
                  ) : (
                    <ChevronRight
                      size={16}
                      className="text-slate-400 shrink-0"
                      aria-hidden="true"
                    />
                  )}
                  <Tag
                    size={14}
                    className="text-reclaw-600 dark:text-reclaw-400 shrink-0"
                    aria-hidden="true"
                  />
                  <span className="font-medium text-sm text-slate-900 dark:text-white truncate">
                    {code.label}
                  </span>
                  {code.parent_theme && (
                    <span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-1.5 py-0.5 rounded shrink-0">
                      {code.parent_theme}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-2">
                  {code.frequency > 0 && (
                    <span className="text-xs text-slate-400">
                      {code.frequency}x
                    </span>
                  )}
                  <span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-1.5 py-0.5 rounded">
                    {code.coding_method}
                  </span>
                </div>
              </button>

              {/* Expanded details */}
              {isExpanded && (
                <div className="border-t border-slate-200 dark:border-slate-700 p-4 space-y-3 bg-slate-50/50 dark:bg-slate-800/20">
                  {/* Brief definition (always visible when expanded) */}
                  <div>
                    <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      Brief Definition
                    </h4>
                    <p className="text-sm text-slate-900 dark:text-white">
                      {code.brief_definition || "Not defined"}
                    </p>
                  </div>

                  {/* Remaining fields */}
                  {CODE_FIELDS.filter((f) => f.key !== "brief_definition").map(
                    (field) => {
                      const value = code[field.key];
                      if (!value) return null;
                      return (
                        <div key={field.key}>
                          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                            {field.label}
                          </h4>
                          <p className="text-sm text-slate-700 dark:text-slate-300">
                            {String(value)}
                          </p>
                        </div>
                      );
                    }
                  )}

                  {/* Exclusion criteria highlighted */}
                  {code.exclusion_criteria && (
                    <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-md p-2.5">
                      <h4 className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wide mb-1">
                        Exclusion Criteria
                      </h4>
                      <p className="text-sm text-red-700 dark:text-red-300">
                        {code.exclusion_criteria}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
