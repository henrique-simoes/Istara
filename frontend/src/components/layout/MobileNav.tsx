"use client";

import { useEffect, useMemo, useState } from "react";
import { MoreHorizontal, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  isMobileMoreView,
  mobileMoreItemsForRole,
  mobilePrimaryItemsForRole,
} from "@/lib/navigation";

interface MobileNavProps {
  activeView: string;
  onViewChange: (view: string) => void;
  onSearchOpen?: () => void;
  userRole?: string | null;
}

export default function MobileNav({ activeView, onViewChange, onSearchOpen, userRole }: MobileNavProps) {
  const [moreOpen, setMoreOpen] = useState(false);
  const primaryItems = useMemo(() => mobilePrimaryItemsForRole(userRole), [userRole]);
  const moreItems = useMemo(() => mobileMoreItemsForRole(userRole), [userRole]);
  const moreActive = isMobileMoreView(activeView, userRole);

  useEffect(() => {
    setMoreOpen(false);
  }, [activeView]);

  useEffect(() => {
    if (!moreOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMoreOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [moreOpen]);

  const navigate = (view: string) => {
    onViewChange(view);
    setMoreOpen(false);
  };

  return (
    <>
      {moreOpen && (
        <div className="lg:hidden fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Mobile navigation menu">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/40"
            aria-label="Close mobile navigation menu"
            onClick={() => setMoreOpen(false)}
          />
          <div className="absolute inset-x-0 bottom-0 max-h-[78dvh] rounded-t-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xl safe-bottom">
            <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 px-4 py-3">
              {onSearchOpen && (
                <button
                  type="button"
                  onClick={() => {
                    setMoreOpen(false);
                    onSearchOpen();
                  }}
                  className="flex min-w-0 flex-1 items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-left text-sm text-slate-600 transition-colors hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  aria-label="Search findings (Cmd+K)"
                >
                  <Search size={16} />
                  <span className="truncate">Search...</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => setMoreOpen(false)}
                className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                aria-label="Close mobile navigation menu"
              >
                <X size={18} />
              </button>
            </div>
            <div className="grid max-h-[60dvh] grid-cols-3 gap-2 overflow-y-auto p-3">
              {moreItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => navigate(item.id)}
                  className={cn(
                    "flex min-h-20 flex-col items-center justify-center gap-2 rounded-lg border px-2 py-3 text-center transition-colors",
                    activeView === item.id
                      ? "border-istara-300 bg-istara-50 text-istara-700 dark:border-istara-700 dark:bg-istara-900/30 dark:text-istara-300"
                      : "border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-400 dark:hover:bg-slate-800"
                  )}
                  aria-current={activeView === item.id ? "page" : undefined}
                  aria-label={item.label}
                >
                  <item.icon size={20} />
                  <span className="max-w-full text-[11px] font-medium leading-tight">{item.shortLabel || item.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <nav
        className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 safe-bottom"
        aria-label="Mobile navigation"
      >
        <div className="grid h-14 grid-cols-5 items-center">
          {primaryItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => navigate(item.id)}
              className={cn(
                "flex h-full flex-col items-center justify-center gap-0.5 rounded-lg px-1 py-1 transition-colors",
                activeView === item.id ? "text-istara-600 dark:text-istara-400" : "text-slate-400"
              )}
              aria-current={activeView === item.id ? "page" : undefined}
              aria-label={item.label}
            >
              <item.icon size={20} />
              <span className="max-w-full truncate text-[10px]">{item.shortLabel || item.label}</span>
            </button>
          ))}
          <button
            type="button"
            onClick={() => setMoreOpen((open) => !open)}
            className={cn(
              "flex h-full flex-col items-center justify-center gap-0.5 rounded-lg px-1 py-1 transition-colors",
              moreActive || moreOpen ? "text-istara-600 dark:text-istara-400" : "text-slate-400"
            )}
            aria-label="More views"
            aria-expanded={moreOpen}
          >
            <MoreHorizontal size={20} />
            <span className="text-[10px]">More</span>
          </button>
        </div>
      </nav>
    </>
  );
}
