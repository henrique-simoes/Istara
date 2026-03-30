"use client";

import { useState } from "react";
import { User, LogOut, Settings, ChevronUp } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils";

interface UserMenuProps {
  collapsed?: boolean;
}

export default function UserMenu({ collapsed }: UserMenuProps) {
  const { user, teamMode, logout } = useAuthStore();
  const [open, setOpen] = useState(false);

  if (!teamMode && !user) {
    return null;
  }

  const displayName = user?.display_name || user?.username || "Local User";
  const role = user?.role || "admin";

  return (
    <div className="relative border-t border-slate-200 dark:border-slate-800 p-2">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-label="User menu"
        className={cn(
          "flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm transition-colors",
          "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400"
        )}
      >
        <div className="w-7 h-7 rounded-full bg-istara-100 dark:bg-istara-900/30 flex items-center justify-center">
          <User size={14} className="text-istara-600 dark:text-istara-400" />
        </div>
        {!collapsed && (
          <>
            <div className="flex-1 text-left">
              <div className="truncate font-medium text-slate-800 dark:text-slate-200">{displayName}</div>
              <div className="text-xs text-slate-400 capitalize">{role}</div>
            </div>
            <ChevronUp size={14} className={cn("transition-transform", open ? "" : "rotate-180")} />
          </>
        )}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute bottom-full left-2 right-2 mb-1 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1"
        >
          <button
            role="menuitem"
            onClick={() => {
              setOpen(false);
              window.dispatchEvent(new CustomEvent("istara:navigate", { detail: { view: "settings" } }));
            }}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
          >
            <Settings size={14} />
            Preferences
          </button>
          {teamMode && (
            <button
              role="menuitem"
              onClick={() => {
                logout();
                setOpen(false);
              }}
              className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              <LogOut size={14} />
              Sign Out
            </button>
          )}
        </div>
      )}
    </div>
  );
}
