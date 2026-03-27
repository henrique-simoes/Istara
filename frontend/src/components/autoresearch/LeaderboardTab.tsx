"use client";

import { useEffect } from "react";
import { Trophy, Cpu, Thermometer, BarChart3, Zap } from "lucide-react";
import { useAutoresearchStore } from "@/stores/autoresearchStore";
import { cn } from "@/lib/utils";

export default function LeaderboardTab() {
  const { leaderboard, loading, fetchLeaderboard } = useAutoresearchStore();

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]);

  // Group leaderboard entries by skill
  const bySkill = leaderboard.reduce<Record<string, typeof leaderboard>>((acc, entry) => {
    if (!acc[entry.skill_name]) acc[entry.skill_name] = [];
    acc[entry.skill_name].push(entry);
    return acc;
  }, {});

  // Sort each skill's entries by best_quality descending
  Object.values(bySkill).forEach((entries) =>
    entries.sort((a, b) => b.best_quality - a.best_quality)
  );

  const skillNames = Object.keys(bySkill).sort();

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <Trophy size={20} className="text-amber-500" />
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          Model + Temperature Leaderboard
        </h2>
      </div>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
        Best-performing model and temperature configuration per skill, ranked by quality score.
      </p>

      {loading && leaderboard.length === 0 ? (
        <div className="text-center py-12 text-slate-400 dark:text-slate-500">
          Loading leaderboard...
        </div>
      ) : skillNames.length === 0 ? (
        <div className="text-center py-12 text-slate-400 dark:text-slate-500">
          No leaderboard data yet. Run some model_temp experiments to populate.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {skillNames.map((skillName) => {
            const entries = bySkill[skillName];
            const best = entries[0];

            return (
              <div
                key={skillName}
                className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden"
              >
                {/* Skill header */}
                <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                  <h3 className="font-semibold text-slate-900 dark:text-white text-sm">
                    {skillName}
                  </h3>
                </div>

                {/* Entries */}
                <div className="divide-y divide-slate-100 dark:divide-slate-800/50">
                  {entries.map((entry, idx) => (
                    <div
                      key={`${entry.skill_name}-${entry.model_name}-${entry.temperature}`}
                      className={cn(
                        "px-4 py-3 flex items-center gap-3",
                        idx === 0 && "bg-green-50/50 dark:bg-green-900/10"
                      )}
                    >
                      {/* Rank */}
                      <span
                        className={cn(
                          "text-xs font-bold w-6 h-6 rounded-full flex items-center justify-center shrink-0",
                          idx === 0
                            ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                        )}
                      >
                        {idx + 1}
                      </span>

                      {/* Model info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Cpu size={14} className="text-slate-400 shrink-0" />
                          <span className="text-sm font-medium text-slate-900 dark:text-white truncate">
                            {entry.model_name}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                            <Thermometer size={12} />
                            {entry.temperature.toFixed(2)}
                          </span>
                          <span className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                            <Zap size={12} />
                            {entry.executions} runs
                          </span>
                        </div>
                      </div>

                      {/* Quality score */}
                      <div className="text-right shrink-0">
                        <div
                          className={cn(
                            "text-sm font-bold",
                            idx === 0
                              ? "text-green-600 dark:text-green-400"
                              : "text-slate-700 dark:text-slate-300"
                          )}
                        >
                          {entry.best_quality.toFixed(3)}
                        </div>
                        <div className="flex items-center gap-1 justify-end">
                          <BarChart3 size={10} className="text-slate-400" />
                          <span className="text-xs text-slate-400 dark:text-slate-500">
                            avg {entry.avg_quality.toFixed(3)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
