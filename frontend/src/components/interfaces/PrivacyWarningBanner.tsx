"use client";

import { AlertTriangle } from "lucide-react";

export default function PrivacyWarningBanner({ service, onAcknowledge }: { service: "Stitch" | "Figma"; onAcknowledge: () => void }) {
  return (
    <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="text-amber-500 shrink-0 mt-0.5" size={20} />
        <div className="flex-1">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
            External Data Sharing
          </p>
          <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
            This action sends data to {service}. This breaks Istara&apos;s local-first approach.
            Your research data, prompts, and generated designs will be shared with external services.
          </p>
          <button onClick={onAcknowledge} className="mt-2 text-sm font-medium text-amber-800 dark:text-amber-200 underline hover:no-underline">
            I understand, proceed
          </button>
        </div>
      </div>
    </div>
  );
}
