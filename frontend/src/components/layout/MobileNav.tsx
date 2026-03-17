"use client";

import { Bot, Diamond, LayoutDashboard, Mic, FileText, Wand2, Users } from "lucide-react";
import { cn } from "@/lib/utils";

interface MobileNavProps {
  activeView: string;
  onViewChange: (view: string) => void;
}

const NAV_ITEMS = [
  { id: "chat", icon: Bot, label: "Chat" },
  { id: "findings", icon: Diamond, label: "Findings" },
  { id: "tasks", icon: LayoutDashboard, label: "Tasks" },
  { id: "interviews", icon: Mic, label: "Interviews" },
  { id: "context", icon: FileText, label: "Context" },
  { id: "skills", icon: Wand2, label: "Skills" },
  { id: "agents", icon: Users, label: "Agents" },
];

/**
 * Bottom navigation bar for mobile/narrow screens.
 * Replaces sidebar when viewport < 1024px.
 */
export default function MobileNav({ activeView, onViewChange }: MobileNavProps) {
  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 safe-bottom">
      <div className="flex justify-around items-center h-14">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => onViewChange(item.id)}
            className={cn(
              "flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg transition-colors",
              activeView === item.id
                ? "text-reclaw-600"
                : "text-slate-400"
            )}
            aria-label={item.label}
          >
            <item.icon size={20} />
            <span className="text-[10px]">{item.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}
