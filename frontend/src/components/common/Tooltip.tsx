"use client";

import { useState, useRef } from "react";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface TooltipProps {
  text: string;
  children?: React.ReactNode;
  position?: "top" | "bottom" | "left" | "right";
}

/**
 * Glossary/tooltip for UXR terms.
 * Hover or focus to see the definition.
 */
export default function Tooltip({ text, children, position = "top" }: TooltipProps) {
  const [show, setShow] = useState(false);

  const positionClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  return (
    <span
      className="relative inline-flex items-center"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onFocus={() => setShow(true)}
      onBlur={() => setShow(false)}
    >
      {children || (
        <button
          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
          aria-label={text}
          tabIndex={0}
        >
          <HelpCircle size={14} />
        </button>
      )}
      {show && (
        <span
          role="tooltip"
          className={cn(
            "absolute z-50 px-3 py-2 text-xs text-white bg-slate-800 dark:bg-slate-700 rounded-lg shadow-lg max-w-xs whitespace-normal",
            positionClasses[position]
          )}
        >
          {text}
          <span className={cn(
            "absolute w-2 h-2 bg-slate-800 dark:bg-slate-700 rotate-45",
            position === "top" && "top-full left-1/2 -translate-x-1/2 -mt-1",
            position === "bottom" && "bottom-full left-1/2 -translate-x-1/2 -mb-1",
          )} />
        </span>
      )}
    </span>
  );
}

/** Common UXR glossary terms */
export const GLOSSARY = {
  nugget: "A raw piece of evidence — a direct quote, observation, or data point from research.",
  fact: "A verified claim supported by one or more nuggets. Objective, evidence-based.",
  insight: "A pattern or conclusion synthesized from multiple facts. The 'why' behind the data.",
  recommendation: "An actionable suggestion based on insights. The 'what to do' derived from research.",
  "double-diamond": "A design framework with 4 phases: Discover (diverge), Define (converge), Develop (diverge), Deliver (converge).",
  "atomic-research": "A methodology that breaks research into reusable atoms: Nuggets → Facts → Insights → Recommendations.",
  sus: "System Usability Scale — a 10-item questionnaire giving a score from 0-100. Average is 68.",
  nps: "Net Promoter Score — measures loyalty. Promoters (9-10) minus Detractors (0-6). Range: -100 to +100.",
  rag: "Retrieval-Augmented Generation — the AI retrieves relevant documents before generating a response.",
  kappa: "Cohen's Kappa — a statistic measuring inter-rater agreement beyond chance. ≥0.6 is moderate, ≥0.8 is excellent.",
};
