"use client";

import { Scale } from "lucide-react";
import type { CodeApplicationType } from "@/lib/types";

/** Decision-model triage note for one review item. The backend sends it only for items a trusted
 * scope routed, never for shadow or blind-audit items, so it cannot anchor the reviewer. */
export default function DeciderTriageNote({ triage }: { triage: CodeApplicationType["decider_triage"] }) {
  if (!triage) return null;
  const probability =
    triage.p_supports === null ? "" : ` · ${Math.round(triage.p_supports * 100)}% that the excerpt supports the code`;
  return (
    <div
      className="mb-3 flex items-start gap-2 rounded-md border border-sky-200 bg-sky-50 p-2.5 text-xs text-sky-900 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-100"
      aria-label="Decision model triage"
    >
      <Scale size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
      <p className="leading-relaxed">
        <strong>{triage.action === "abstain" ? "Decision model was unsure" : "Decision model flagged this"}</strong>
        {probability}. It moved this item up the queue; your decision is still the only one that counts.
      </p>
    </div>
  );
}
