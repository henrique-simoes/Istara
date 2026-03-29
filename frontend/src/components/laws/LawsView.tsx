"use client";

import { useEffect } from "react";
import { BookOpen, BarChart3 } from "lucide-react";
import { useLawsStore } from "@/stores/lawsStore";
import { cn } from "@/lib/utils";
import LawsCatalog from "./LawsCatalog";
import ComplianceProfile from "./ComplianceProfile";
import ViewOnboarding from "@/components/common/ViewOnboarding";

type LawsTab = "catalog" | "compliance";

const TABS: { id: LawsTab; icon: any; label: string }[] = [
  { id: "catalog", icon: BookOpen, label: "Catalog" },
  { id: "compliance", icon: BarChart3, label: "Compliance" },
];

export default function LawsView() {
  const { activeTab, setActiveTab, fetchLaws } = useLawsStore();

  useEffect(() => {
    fetchLaws();
  }, [fetchLaws]);

  const renderTab = () => {
    switch (activeTab) {
      case "catalog":
        return <LawsCatalog />;
      case "compliance":
        return <ComplianceProfile />;
      default:
        return <LawsCatalog />;
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <ViewOnboarding viewId="laws" title="Laws of UX Compliance" description="30 Laws of UX (Yablonski, 2024) with compliance scoring. See which laws your design violates based on evaluation findings." chatPrompt="What are the Laws of UX?" />
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors",
              activeTab === tab.id
                ? "bg-reclaw-100 text-reclaw-700 dark:bg-reclaw-900/30 dark:text-reclaw-400"
                : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            )}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Active tab content */}
      {renderTab()}
    </div>
  );
}
