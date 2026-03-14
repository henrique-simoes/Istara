"use client";

import { useEffect, useState } from "react";

interface CelebrationProps {
  trigger: boolean;
  message: string;
  emoji?: string;
}

/**
 * Brief celebration animation for milestones.
 * Shows a centered emoji + message that fades out.
 */
export default function Celebration({ trigger, message, emoji = "🎉" }: CelebrationProps) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (trigger) {
      setShow(true);
      const timer = setTimeout(() => setShow(false), 2500);
      return () => clearTimeout(timer);
    }
  }, [trigger]);

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
      <div className="animate-fade-in text-center">
        <div className="text-6xl celebrate mb-3">{emoji}</div>
        <p className="text-lg font-bold text-slate-900 dark:text-white bg-white/90 dark:bg-slate-900/90 rounded-xl px-6 py-3 shadow-xl">
          {message}
        </p>
      </div>
      {/* Confetti particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 rounded-full"
            style={{
              backgroundColor: ["#22c55e", "#3b82f6", "#eab308", "#ef4444", "#a855f7"][i % 5],
              left: `${Math.random() * 100}%`,
              top: "-10px",
              animation: `confetti-fall ${1.5 + Math.random()}s ease-out forwards`,
              animationDelay: `${Math.random() * 0.5}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
