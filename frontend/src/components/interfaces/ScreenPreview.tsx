"use client";

import { useMemo } from "react";

const DEVICE_SIZES: Record<string, { width: number; height: number }> = {
  MOBILE: { width: 375, height: 812 },
  DESKTOP: { width: 1280, height: 800 },
  TABLET: { width: 768, height: 1024 },
  AGNOSTIC: { width: 1024, height: 768 },
};

export default function ScreenPreview({ html, deviceType }: { html: string; deviceType?: string }) {
  const size = DEVICE_SIZES[deviceType || "DESKTOP"] || DEVICE_SIZES.DESKTOP;

  const scaleFactor = useMemo(() => {
    // Scale to fit within a max container width of 800px
    const maxWidth = 800;
    return size.width > maxWidth ? maxWidth / size.width : 1;
  }, [size.width]);

  if (!html) {
    return (
      <div className="flex items-center justify-center h-48 bg-slate-100 dark:bg-slate-800 rounded-lg text-slate-400 text-sm">
        No HTML content to preview
      </div>
    );
  }

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden bg-white">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-400" />
          <div className="w-3 h-3 rounded-full bg-yellow-400" />
          <div className="w-3 h-3 rounded-full bg-green-400" />
        </div>
        <span className="text-xs text-slate-400 ml-2">
          {deviceType || "DESKTOP"} - {size.width} x {size.height}
        </span>
      </div>
      <div
        className="overflow-auto"
        style={{ maxHeight: "600px" }}
      >
        <iframe
          srcDoc={html}
          sandbox="allow-scripts"
          title="Screen preview"
          style={{
            width: size.width,
            height: size.height,
            transform: `scale(${scaleFactor})`,
            transformOrigin: "top left",
            border: "none",
          }}
        />
      </div>
    </div>
  );
}
