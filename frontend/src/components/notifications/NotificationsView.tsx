"use client";

import { useEffect } from "react";
import { Bell, Settings2 } from "lucide-react";
import { useNotificationStore } from "@/stores/notificationStore";
import { cn } from "@/lib/utils";
import NotificationListTab from "./NotificationListTab";
import NotificationPrefsTab from "./NotificationPrefsTab";
import ViewOnboarding from "@/components/common/ViewOnboarding";

type NotificationsTab = "all" | "preferences";

const TABS: { id: NotificationsTab; icon: any; label: string }[] = [
  { id: "all", icon: Bell, label: "All Notifications" },
  { id: "preferences", icon: Settings2, label: "Preferences" },
];

export default function NotificationsView() {
  const { activeTab, setActiveTab, fetchNotifications, fetchUnreadCount, unreadCount } = useNotificationStore();

  useEffect(() => {
    fetchNotifications();
    fetchUnreadCount();
  }, [fetchNotifications, fetchUnreadCount]);

  const renderTab = () => {
    switch (activeTab) {
      case "all": return <NotificationListTab />;
      case "preferences": return <NotificationPrefsTab />;
      default: return <NotificationListTab />;
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <ViewOnboarding viewId="notifications" title="Activity Feed" description="Notifications from agents, skills, and system events. Filter by category, severity, or agent." chatPrompt="What triggers notifications?" />
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors",
              activeTab === tab.id
                ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            )}
          >
            <tab.icon size={16} />
            {tab.label}
            {tab.id === "all" && unreadCount > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-red-600 text-white">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Active tab content */}
      {renderTab()}
    </div>
  );
}
