"use client";

import { useEffect } from "react";
import { Bot, Wand2, LayoutGrid, ExternalLink, FileOutput } from "lucide-react";
import { useInterfacesStore } from "@/stores/interfacesStore";
import { cn } from "@/lib/utils";
import InterfacesOnboarding from "./InterfacesOnboarding";
import DesignChatTab from "./DesignChatTab";
import GenerateTab from "./GenerateTab";
import ScreensGalleryTab from "./ScreensGalleryTab";
import FigmaTab from "./FigmaTab";
import HandoffTab from "./HandoffTab";

type InterfacesTab = "design-chat" | "generate" | "screens" | "figma" | "handoff";

const TABS: { id: InterfacesTab; icon: any; label: string }[] = [
  { id: "design-chat", icon: Bot, label: "Design Chat" },
  { id: "generate", icon: Wand2, label: "Generate" },
  { id: "screens", icon: LayoutGrid, label: "Screens" },
  { id: "figma", icon: ExternalLink, label: "Figma" },
  { id: "handoff", icon: FileOutput, label: "Handoff" },
];

export default function InterfacesView() {
  const { activeTab, setActiveTab, status, fetchStatus, onboardingDismissed } = useInterfacesStore();

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const showOnboarding = status?.onboarding_needed && !onboardingDismissed;

  const renderTab = () => {
    switch (activeTab) {
      case "design-chat": return <DesignChatTab />;
      case "generate": return <GenerateTab />;
      case "screens": return <ScreensGalleryTab />;
      case "figma": return <FigmaTab />;
      case "handoff": return <HandoffTab />;
      default: return <DesignChatTab />;
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
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

      {/* Onboarding overlay */}
      {showOnboarding && <InterfacesOnboarding />}
    </div>
  );
}
