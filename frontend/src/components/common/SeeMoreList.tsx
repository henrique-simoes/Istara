"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

const DEFAULT_VISIBLE = 5;

/**
 * Collapsible long list for Settings cards. Shows the first `visibleCount`
 * items and a `Click to see N more {noun}` toggle once the list grows past
 * it — the same interaction language as the Active Sessions card.
 */
export default function SeeMoreList<T>({
  items,
  renderItem,
  noun,
  pluralNoun,
  visibleCount = DEFAULT_VISIBLE,
  listClassName = "space-y-2",
  listId,
}: {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  noun: string;
  pluralNoun?: string;
  visibleCount?: number;
  listClassName?: string;
  listId: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const collapsed = items.length > visibleCount && !expanded;
  const visible = collapsed ? items.slice(0, visibleCount) : items;
  const hidden = items.length - visibleCount;
  const many = hidden === 1 ? noun : pluralNoun || `${noun}s`;

  return (
    <div>
      <div className={listClassName} id={listId}>
        {visible.map((item, index) => renderItem(item, index))}
      </div>
      {items.length > visibleCount && (
        <div className="pt-2 text-center">
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            aria-controls={listId}
            className="inline-flex min-h-[44px] items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 transition-colors"
          >
            {expanded ? (
              <>
                <ChevronUp size={14} aria-hidden="true" />
                Show fewer {pluralNoun || `${noun}s`}
              </>
            ) : (
              <>
                <ChevronDown size={14} aria-hidden="true" />
                Click to see {hidden} more {many}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
