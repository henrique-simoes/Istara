"use client";

import { useState } from "react";
import { CheckCircle2, ClipboardList, Loader2, Send, Sparkles, Trash2 } from "lucide-react";
import { post } from "@/lib/apiClient";

interface QuestionnaireStudioProps {
  projectId: string | null;
  onRecorded: () => void;
}

const FIELD =
  "w-full px-3 py-1.5 text-xs border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-istara-500";

/**
 * Records answers a real participant gave another way (a phone call, a paper form).
 * It starts empty: pre-filled sample answers would be one click away from becoming fabricated
 * evidence, and an unanswered question is skipped, never stored as an invented answer.
 */
export default function QuestionnaireStudio({ projectId, onRecorded }: QuestionnaireStudioProps) {
  const [surveyTitle, setSurveyTitle] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [newQuestionText, setNewQuestionText] = useState("");
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [studioError, setStudioError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [recorded, setRecorded] = useState<{ nuggets: number; evidence_units: number } | null>(null);

  const addQuestion = () => {
    if (!newQuestionText.trim()) return;
    setQuestions([...questions, newQuestionText.trim()]);
    setNewQuestionText("");
  };

  const record = async () => {
    if (!projectId || submitting) return;
    const answered = questions.filter((_, idx) => (answers[idx] || "").trim());
    if (!surveyTitle.trim() || answered.length === 0) {
      setStudioError("Give the survey a name and enter at least one answer before recording.");
      return;
    }
    setSubmitting(true);
    setRecorded(null);
    setStudioError(null);
    try {
      const resp = await post<{ nuggets_created?: number; evidence_units_created?: number }>(
        "/api/surveys/responses/ingest",
        {
          project_id: projectId,
          survey_name: surveyTitle,
          responses: [
            {
              id: `resp-${Date.now()}`,
              answers: questions.map((q, idx) => ({ question: q, answer: (answers[idx] || "").trim() })),
            },
          ],
        }
      );
      setRecorded({ nuggets: resp.nuggets_created || 0, evidence_units: resp.evidence_units_created || 0 });
      setAnswers({});
      onRecorded();
    } catch (e) {
      setStudioError(e instanceof Error ? `Could not record the response: ${e.message}` : "Could not record the response.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {recorded && (
        <div role="status" className="flex items-center justify-between p-3.5 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300 text-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} />
            <span>
              Recorded {recorded.nuggets} answer{recorded.nuggets === 1 ? "" : "s"} as raw evidence ({recorded.evidence_units} evidence
              unit{recorded.evidence_units === 1 ? "" : "s"}). Analyse them through a task before they reach a report.
            </span>
          </div>
          <button onClick={() => setRecorded(null)} aria-label="Dismiss" className="text-emerald-600 hover:text-emerald-800">×</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <ClipboardList size={16} className="text-purple-600 dark:text-purple-400" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Survey Definition</h3>
            </div>
            <span className="text-[11px] text-slate-500 font-mono">{questions.length} Questions</span>
          </div>
          <div>
            <label htmlFor="studio-survey-title" className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1">Survey Title</label>
            <input
              id="studio-survey-title"
              type="text"
              placeholder="e.g., Onboarding phone survey"
              value={surveyTitle}
              onChange={(e) => setSurveyTitle(e.target.value)}
              className={`${FIELD} bg-slate-50 dark:bg-slate-800`}
            />
          </div>
          <div className="space-y-2.5">
            <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">Questions</p>
            {questions.map((q, idx) => (
              <div key={idx} className="flex items-start gap-2 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/60 text-xs">
                <span className="font-semibold text-purple-600 dark:text-purple-400 shrink-0">Q{idx + 1}:</span>
                <span className="text-slate-800 dark:text-slate-200 flex-1">{q}</span>
                <button
                  onClick={() => setQuestions(questions.filter((_, i) => i !== idx))}
                  className="text-slate-400 hover:text-red-500 transition-colors"
                  aria-label={`Remove question ${idx + 1}`}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
            <div className="flex items-center gap-2 pt-2">
              <input
                type="text"
                aria-label="New survey question"
                placeholder="Add a new survey question..."
                value={newQuestionText}
                onChange={(e) => setNewQuestionText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") addQuestion(); }}
                className={`flex-1 ${FIELD} bg-white dark:bg-slate-800 placeholder:text-slate-400`}
              />
              <button
                onClick={addQuestion}
                className="px-3 py-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg transition-colors shrink-0"
              >
                Add Q
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-blue-600 dark:text-blue-400" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Record a Participant&apos;s Answers</h3>
            </div>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 font-medium">
              Stored as raw evidence
            </span>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            For answers a real participant gave you another way (a phone call, a paper form). Each answer becomes a raw
            evidence unit; empty answers are skipped. Never enter invented answers here.
          </p>
          <div className="space-y-3">
            {questions.length === 0 && (
              <p className="text-xs text-slate-500 dark:text-slate-400">Add the survey&apos;s questions first.</p>
            )}
            {questions.map((q, idx) => (
              <div key={idx} className="space-y-1">
                <label htmlFor={`studio-answer-${idx}`} className="text-xs font-medium text-slate-700 dark:text-slate-300 block">
                  Q{idx + 1}: {q}
                </label>
                <textarea
                  id={`studio-answer-${idx}`}
                  rows={2}
                  value={answers[idx] || ""}
                  onChange={(e) => setAnswers({ ...answers, [idx]: e.target.value })}
                  placeholder="Participant answer..."
                  className={`${FIELD} bg-slate-50 dark:bg-slate-800 font-sans`}
                />
              </div>
            ))}
          </div>
          {studioError && <p role="alert" className="text-xs text-red-600 dark:text-red-400">{studioError}</p>}
          <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end">
            <button
              onClick={record}
              disabled={submitting || !projectId}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg bg-istara-600 hover:bg-istara-700 text-white transition-colors disabled:opacity-50 shadow-xs"
            >
              {submitting ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
              Record response
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
