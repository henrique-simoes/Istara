"use client";

import { useState } from "react";
import { Power, PowerOff, Heart, MessageSquare, Clock } from "lucide-react";
import { channels as channelsApi } from "@/lib/api";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { cn } from "@/lib/utils";
import type { ChannelInstance } from "@/lib/types";

const PLATFORM_META: Record<string, { label: string; color: string; bg: string }> = {
  telegram: { label: "Telegram", color: "text-[#0088cc]", bg: "bg-[#0088cc]/10" },
  slack: { label: "Slack", color: "text-[#4A154B]", bg: "bg-[#4A154B]/10" },
  whatsapp: { label: "WhatsApp", color: "text-[#25D366]", bg: "bg-[#25D366]/10" },
  google_chat: { label: "Google Chat", color: "text-[#00AC47]", bg: "bg-[#00AC47]/10" },
};

const HEALTH_DOT: Record<string, string> = {
  healthy: "bg-green-500",
  unhealthy: "bg-red-500",
  unknown: "bg-yellow-500",
};

interface ChannelInstanceCardProps {
  instance: ChannelInstance;
  onSelect: (id: string) => void;
  selected: boolean;
}

export default function ChannelInstanceCard({ instance, onSelect, selected }: ChannelInstanceCardProps) {
  const { fetchChannels } = useIntegrationsStore();
  const [toggling, setToggling] = useState(false);
  const meta = PLATFORM_META[instance.platform] || { label: instance.platform, color: "text-slate-500", bg: "bg-slate-100" };

  const handleToggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setToggling(true);
    try {
      if (instance.is_active) {
        await channelsApi.stop(instance.id);
      } else {
        await channelsApi.start(instance.id);
      }
      await fetchChannels();
    } catch {
      // silently fail
    } finally {
      setToggling(false);
    }
  };

  const timeAgo = (dateStr: string | null) => {
    if (!dateStr) return "Never";
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <button
      onClick={() => onSelect(instance.id)}
      className={cn(
        "w-full text-left bg-white dark:bg-slate-900 border rounded-xl p-4 transition-all",
        selected
          ? "border-istara-400 dark:border-istara-600 ring-1 ring-istara-200 dark:ring-istara-800"
          : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full", meta.bg, meta.color)}>
            {meta.label}
          </span>
          <span className={cn("w-2 h-2 rounded-full", HEALTH_DOT[instance.health_status] || HEALTH_DOT.unknown)} title={`Health: ${instance.health_status}`} />
        </div>
        <button
          onClick={handleToggle}
          disabled={toggling}
          aria-label={instance.is_active ? "Stop channel" : "Start channel"}
          className={cn(
            "p-1.5 rounded-lg transition-colors",
            instance.is_active
              ? "text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20"
              : "text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          )}
        >
          {instance.is_active ? <Power size={16} /> : <PowerOff size={16} />}
        </button>
      </div>

      <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-2 truncate">
        {instance.name}
      </h3>

      <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-1">
          <MessageSquare size={12} />
          {instance.message_count}
        </span>
        <span className="flex items-center gap-1">
          <Clock size={12} />
          {timeAgo(instance.updated_at)}
        </span>
      </div>
    </button>
  );
}
