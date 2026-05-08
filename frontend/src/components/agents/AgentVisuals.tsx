import Image from "next/image";

import { agents as agentsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Agent, HeartbeatStatus } from "@/lib/types";

export function HeartbeatDot({
  status,
  isActive,
  size = "sm",
}: {
  status: HeartbeatStatus;
  isActive?: boolean;
  size?: "sm" | "md";
}) {
  const sizeClass = size === "md" ? "w-3 h-3" : "w-2 h-2";
  const colors: Record<string, string> = {
    healthy: "bg-green-500",
    degraded: "bg-yellow-500",
    error: "bg-red-500",
    stopped: "bg-slate-400",
  };

  const effectiveStatus = isActive && (status === "stopped" || !colors[status])
    ? "healthy"
    : colors[status]
      ? status
      : "stopped";
  const color = colors[effectiveStatus] || "bg-green-500";

  return (
    <span className="relative inline-flex">
      <span className={cn("rounded-full", sizeClass, color)} />
      {effectiveStatus === "healthy" && (
        <span className={cn("absolute rounded-full animate-ping opacity-75", sizeClass, color)} />
      )}
    </span>
  );
}

export function AgentAvatar({ agent, size = "md" }: { agent: Agent; size?: "sm" | "md" | "lg" }) {
  const sizeClasses = { sm: "w-8 h-8 text-xs", md: "w-10 h-10 text-sm", lg: "w-14 h-14 text-lg" };
  const initial = agent.name.charAt(0).toUpperCase();
  const bgColors = [
    "bg-blue-500",
    "bg-green-500",
    "bg-purple-500",
    "bg-orange-500",
    "bg-pink-500",
    "bg-cyan-500",
    "bg-indigo-500",
    "bg-teal-500",
  ];
  const colorIdx = agent.name.charCodeAt(0) % bgColors.length;

  if (agent.avatar_path) {
    const pixelSize = size === "lg" ? 56 : size === "md" ? 40 : 32;
    return (
      <Image
        src={agentsApi.avatarUrl(agent.id)}
        alt={agent.name}
        width={pixelSize}
        height={pixelSize}
        unoptimized
        className={cn("rounded-full object-cover", sizeClasses[size])}
      />
    );
  }

  return (
    <div
      className={cn(
        "rounded-full flex items-center justify-center text-white font-semibold",
        sizeClasses[size],
        bgColors[colorIdx]
      )}
    >
      {initial}
    </div>
  );
}
