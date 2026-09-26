import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Phone layout for Interviews. Three fixed columns (list 320 px, toggle, tags 288 px) left the
 * interview itself nothing at 375 px. Below the md breakpoint the list and the open interview take
 * turns, and the tags panel opens over the interview, collapsed by default. Desktop is unchanged.
 */
const NARROW_QUERY = "(max-width: 767px)";

/** Whether the screen is below the md breakpoint; false until mounted (server render). */
export function useNarrowScreen(): boolean {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const media = window.matchMedia(NARROW_QUERY);
    const update = () => setNarrow(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return narrow;
}

/** On a phone the list shows when no interview is open or when the user went back to it. */
export function showsList(selectedFile: string | null, listOpen: boolean): boolean {
  return !selectedFile || listOpen;
}

export function explorerClass(listShown: boolean): string {
  return cn(
    "w-full md:w-80 border-r border-slate-200 dark:border-slate-800 flex-col bg-slate-50/50 dark:bg-slate-900/60 shrink-0",
    listShown ? "flex" : "hidden md:flex"
  );
}

export function workspaceClass(listShown: boolean): string {
  return cn("flex-1 flex-col min-w-0 bg-white dark:bg-slate-950 overflow-hidden", listShown ? "hidden md:flex" : "flex");
}

export function inspectorToggleClass(listShown: boolean): string {
  return cn(
    "flex-col items-center justify-start py-2 border-l border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 shrink-0",
    listShown ? "hidden md:flex" : "flex"
  );
}

export const TAGS_PANEL_CLASS =
  "w-72 max-w-[85vw] flex flex-col bg-slate-50 dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shrink-0 fixed inset-y-0 right-0 z-40 shadow-xl md:static md:z-auto md:shadow-none md:bg-slate-50/70";

/** The tags panel starts collapsed on a phone, where it would cover the interview. */
export function useTagsCollapsedOnPhone(setCollapsed: (collapsed: boolean) => void): void {
  const narrow = useNarrowScreen();
  useEffect(() => {
    if (narrow) setCollapsed(true);
  }, [narrow, setCollapsed]);
}
