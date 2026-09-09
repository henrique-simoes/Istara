"use client";

import { useState, useRef, useEffect } from "react";
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX } from "lucide-react";
import { cn } from "@/lib/utils";

interface AudioPlayerProps {
  src: string;
  onTimeUpdate?: (currentTime: number) => void;
  onDurationChange?: (duration: number) => void;
  seekRequestTime?: number | null;
  className?: string;
}

/**
 * Audio player for interview recordings.
 * Syncs with transcript when onTimeUpdate is provided.
 * Meets WCAG 2.2 AA contrast, 44px primary touch target, and full dark mode styling.
 */
export default function AudioPlayer({
  src,
  onTimeUpdate,
  onDurationChange,
  seekRequestTime,
  className,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [muted, setMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      onTimeUpdate?.(audio.currentTime);
    };
    const handleLoadedMetadata = () => {
      setDuration(audio.duration || 0);
      onDurationChange?.(audio.duration || 0);
    };
    const handleEnded = () => setPlaying(false);

    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("ended", handleEnded);

    return () => {
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("ended", handleEnded);
    };
  }, [onTimeUpdate, onDurationChange]);

  useEffect(() => {
    if (seekRequestTime !== undefined && seekRequestTime !== null && audioRef.current) {
      audioRef.current.currentTime = seekRequestTime;
      setCurrentTime(seekRequestTime);
    }
  }, [seekRequestTime]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      setPlaying(false);
    } else {
      audio.play().catch(() => {});
      setPlaying(true);
    }
  };

  const skip = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    const next = Math.max(0, Math.min(audio.currentTime + seconds, duration || 0));
    audio.currentTime = next;
    setCurrentTime(next);
  };

  const seek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;
    const target = Number(e.target.value);
    audio.currentTime = target;
    setCurrentTime(target);
  };

  const cycleRate = () => {
    const rates = [0.75, 1, 1.25, 1.5, 2];
    const idx = rates.indexOf(playbackRate);
    const next = rates[(idx + 1) % rates.length];
    setPlaybackRate(next);
    if (audioRef.current) audioRef.current.playbackRate = next;
  };

  const formatTime = (s: number) => {
    if (!s || isNaN(s)) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div
      className={cn(
        "bg-slate-100 dark:bg-slate-800 rounded-xl p-3.5 border border-slate-200 dark:border-slate-700/60 shadow-sm",
        className
      )}
      role="region"
      aria-label="Interview audio controls"
    >
      <audio ref={audioRef} src={src} muted={muted} />

      {/* Progress bar */}
      <input
        type="range"
        min={0}
        max={duration || 0}
        step={0.1}
        value={currentTime}
        onChange={seek}
        className="w-full h-2 rounded-full appearance-none bg-slate-300 dark:bg-slate-700 cursor-pointer accent-istara-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-istara-500"
        aria-label="Audio progress position"
      />

      <div className="flex items-center justify-between mt-2.5">
        {/* Time */}
        <span className="text-xs font-mono text-slate-500 dark:text-slate-400 min-w-[90px] select-none">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>

        {/* Primary Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => skip(-10)}
            aria-label="Skip backward 10 seconds"
            title="Skip backward 10s"
            className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-200 dark:hover:bg-slate-700/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-istara-500 transition-colors"
          >
            <SkipBack size={16} />
          </button>
          <button
            onClick={togglePlay}
            aria-label={playing ? "Pause interview audio" : "Play interview audio"}
            title={playing ? "Pause" : "Play"}
            className="p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-full bg-istara-600 text-white hover:bg-istara-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-istara-500 shadow-sm transition-transform active:scale-95"
          >
            {playing ? <Pause size={18} /> : <Play size={18} className="translate-x-0.5" />}
          </button>
          <button
            onClick={() => skip(10)}
            aria-label="Skip forward 10 seconds"
            title="Skip forward 10s"
            className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-200 dark:hover:bg-slate-700/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-istara-500 transition-colors"
          >
            <SkipForward size={16} />
          </button>
        </div>

        {/* Secondary controls (Speed & Volume) */}
        <div className="flex items-center gap-1.5 min-w-[90px] justify-end">
          <button
            onClick={cycleRate}
            aria-label={`Playback speed is ${playbackRate}x. Click to cycle`}
            title={`Speed: ${playbackRate}x`}
            className="text-xs font-mono px-2 py-1 min-h-[36px] min-w-[42px] flex items-center justify-center rounded-md bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-600 font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-istara-500 transition-colors"
          >
            {playbackRate}x
          </button>
          <button
            onClick={() => setMuted(!muted)}
            aria-label={muted ? "Unmute audio" : "Mute audio"}
            title={muted ? "Unmute" : "Mute"}
            className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-200 dark:hover:bg-slate-700/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-istara-500 transition-colors"
          >
            {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
          </button>
        </div>
      </div>
    </div>
  );
}
