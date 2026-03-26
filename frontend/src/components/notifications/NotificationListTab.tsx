"use client";

import { useEffect, useState } from "react";
import {
  CheckCheck, Search, X, ChevronLeft, ChevronRight, Bell,
  AlertTriangle, Info, CheckCircle, XCircle, Filter,
  Clock, Trash2,
} from "lucide-react";
import { useNotificationStore } from "@/stores/notificationStore";
import { useAgentStore } from "@/stores/agentStore";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";
import CategoryFilter from "./CategoryFilter";
import type { AppNotification, NotificationSeverity } from "@/lib/types";

const SEVERITY_ICONS: Record<NotificationSeverity, any> = {
  info: Info,
  warning: AlertTriangle,
  error: XCircle,
  success: CheckCircle,
};

const SEVERITY_COLORS: Record<NotificationSeverity, string> = {
  info: "text-blue-600 dark:text-blue-400",
  warning: "text-yellow-600 dark:text-yellow-400",
  error: "text-red-600 dark:text-red-400",
  success: "text-green-600 dark:text-green-400",
};

const CATEGORY_BADGES: Record<string, string> = {
  agent_status: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  task_progress: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  finding_created: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400",
  file_processed: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
  suggestion: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  resource_throttle: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  scheduled_reminder: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400",
  document: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
  loop_execution: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  system: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400",
};

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  if (diff < 60_000) return "Just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function NotificationListTab() {
  const {
    notifications, page, totalPages, total, loading, filters,
    fetchNotifications, markRead, markAllRead, deleteNotification,
    setFilter, clearFilters, unreadCount,
  } = useNotificationStore();
  const { agents, fetchAgents } = useAgentStore();
  const { projects, fetchProjects } = useProjectStore();
  const [showFilters, setShowFilters] = useState(true);

  useEffect(() => {
    fetchAgents();
    fetchProjects();
  }, [fetchAgents, fetchProjects]);

  const applyFilters = () => {
    fetchNotifications(1);
  };

  const handleClearFilters = () => {
    clearFilters();
    fetchNotifications(1);
  };

  const handleNotificationClick = (notification: AppNotification) => {
    if (!notification.read) {
      markRead(notification.id);
    }
    if (notification.action_target) {
      window.dispatchEvent(
        new CustomEvent("reclaw:navigate", { detail: notification.action_target })
      );
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Filter sidebar */}
      <div className={cn(
        "border-r border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 transition-all overflow-y-auto",
        showFilters ? "w-64 p-4" : "w-0 p-0 overflow-hidden"
      )}>
        {showFilters && (
          <div className="space-y-4">
            {/* Category filter */}
            <CategoryFilter
              selected={filters.categories}
              onChange={(categories) => setFilter("categories", categories)}
            />

            {/* Severity */}
            <div className="space-y-2">
              <span className="text-xs font-medium text-slate-700 dark:text-slate-300">Severity</span>
              {(["info", "warning", "error", "success"] as const).map((sev) => (
                <label key={sev} className="flex items-center gap-2 py-0.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.severities.includes(sev)}
                    onChange={() => {
                      const current = filters.severities;
                      setFilter(
                        "severities",
                        current.includes(sev) ? current.filter((s: string) => s !== sev) : [...current, sev]
                      );
                    }}
                    className="rounded border-slate-300 dark:border-slate-600 text-reclaw-600 focus:ring-reclaw-500 focus:ring-offset-0"
                  />
                  <span className="text-xs text-slate-600 dark:text-slate-400 capitalize">{sev}</span>
                </label>
              ))}
            </div>

            {/* Agent dropdown */}
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Agent</label>
              <select
                value={filters.agent_id}
                onChange={(e) => setFilter("agent_id", e.target.value)}
                className="w-full px-2 py-1.5 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              >
                <option value="">All agents</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>

            {/* Project dropdown */}
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Project</label>
              <select
                value={filters.project_id}
                onChange={(e) => setFilter("project_id", e.target.value)}
                className="w-full px-2 py-1.5 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              >
                <option value="">All projects</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            {/* Search */}
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Search</label>
              <div className="relative">
                <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={filters.search}
                  onChange={(e) => setFilter("search", e.target.value)}
                  placeholder="Search notifications..."
                  className="w-full pl-7 pr-2 py-1.5 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                />
              </div>
            </div>

            {/* Date range */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[10px] text-slate-500 mb-0.5">From</label>
                <input
                  type="date"
                  value={filters.from_date}
                  onChange={(e) => setFilter("from_date", e.target.value)}
                  className="w-full px-2 py-1 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-500 mb-0.5">To</label>
                <input
                  type="date"
                  value={filters.to_date}
                  onChange={(e) => setFilter("to_date", e.target.value)}
                  className="w-full px-2 py-1 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={applyFilters}
                className="flex-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-reclaw-600 text-white hover:bg-reclaw-700"
              >
                Apply
              </button>
              <button
                onClick={handleClearFilters}
                className="px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800"
              >
                Clear
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
              aria-label={showFilters ? "Hide filters" : "Show filters"}
            >
              <Filter size={14} />
            </button>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {total} notification{total !== 1 ? "s" : ""}
              {unreadCount > 0 && <span className="ml-1 text-reclaw-600 dark:text-reclaw-400">({unreadCount} unread)</span>}
            </span>
          </div>
          <button
            onClick={() => markAllRead()}
            className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <CheckCheck size={14} />
            Mark all read
          </button>
        </div>

        {/* Notification list */}
        <div className="flex-1 overflow-y-auto" role="list" aria-label="Notifications">
          {notifications.length === 0 && !loading ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400 dark:text-slate-500">
              <Bell size={40} className="mb-3 opacity-50" />
              <p className="text-sm">No notifications yet</p>
            </div>
          ) : (
            notifications.map((notification) => {
              const SeverityIcon = SEVERITY_ICONS[notification.severity] || Info;
              return (
                <div
                  key={notification.id}
                  role="listitem"
                  tabIndex={0}
                  onClick={() => handleNotificationClick(notification)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      handleNotificationClick(notification);
                    }
                  }}
                  className={cn(
                    "flex items-start gap-3 px-4 py-3 cursor-pointer border-b border-slate-100 dark:border-slate-800 transition-colors",
                    "hover:bg-slate-50 dark:hover:bg-slate-800",
                    "focus:outline-none focus:bg-slate-100 dark:focus:bg-slate-800 focus:ring-2 focus:ring-inset focus:ring-reclaw-500",
                    !notification.read && "bg-blue-50/60 dark:bg-blue-900/20"
                  )}
                >
                  <SeverityIcon
                    size={16}
                    className={cn("shrink-0 mt-0.5", SEVERITY_COLORS[notification.severity])}
                    aria-hidden="true"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className={cn(
                        "text-sm truncate text-slate-900 dark:text-white",
                        !notification.read && "font-semibold"
                      )}>
                        {notification.title}
                      </p>
                      <div className="flex items-center gap-2 shrink-0">
                        {!notification.read && (
                          <span className="w-2 h-2 rounded-full bg-reclaw-500" aria-hidden="true" />
                        )}
                        <button
                          onClick={(e) => { e.stopPropagation(); deleteNotification(notification.id); }}
                          className="p-0.5 rounded hover:bg-slate-200 dark:hover:bg-slate-700 opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500"
                          aria-label="Delete notification"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5 line-clamp-2">
                      {notification.message}
                    </p>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
                        CATEGORY_BADGES[notification.category] || CATEGORY_BADGES.system
                      )}>
                        {notification.category.replace(/_/g, " ")}
                      </span>
                      {notification.agent_id && (
                        <span className="text-[10px] text-slate-400 dark:text-slate-500">
                          Agent: {agents.find((a) => a.id === notification.agent_id)?.name || notification.agent_id.slice(0, 8)}
                        </span>
                      )}
                      <span className="flex items-center gap-1 text-[10px] text-slate-400 dark:text-slate-500 ml-auto">
                        <Clock size={10} />
                        {formatTimeAgo(notification.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 py-2 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
            <button
              onClick={() => fetchNotifications(page - 1)}
              disabled={page <= 1}
              className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed text-slate-600 dark:text-slate-400"
              aria-label="Previous page"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="text-xs text-slate-600 dark:text-slate-400">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => fetchNotifications(page + 1)}
              disabled={page >= totalPages}
              className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed text-slate-600 dark:text-slate-400"
              aria-label="Next page"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
