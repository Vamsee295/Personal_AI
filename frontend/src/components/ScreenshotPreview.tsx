import React, { useState, useCallback } from "react";
import { Camera, RefreshCw, Eye, Clock } from "lucide-react";
import { getScreenshot, getLatestScreenshotUrl } from "@/lib/agentApi";

interface ScreenshotPreviewProps {
  screenshotUrl?: string | null;
  onCapture?: (url: string) => void;
  className?: string;
}

export default function ScreenshotPreview({
  screenshotUrl,
  onCapture,
  className = "",
}: ScreenshotPreviewProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [capturedAt, setCapturedAt] = useState<Date | null>(null);
  const [localUrl, setLocalUrl] = useState<string | null>(null);

  const activeUrl = localUrl || screenshotUrl;

  const handleCapture = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getScreenshot();
      if (result.success && result.data?.image_base64) {
        const dataUrl = `data:image/png;base64,${result.data.image_base64}`;
        setLocalUrl(dataUrl);
        setCapturedAt(new Date());
        onCapture?.(dataUrl);
      } else {
        setError(result.error || "Screenshot failed");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [onCapture]);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Try latest file from backend first
      const latestUrl = getLatestScreenshotUrl();
      const res = await fetch(latestUrl);
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        setLocalUrl(url);
        setCapturedAt(new Date());
        onCapture?.(url);
      } else {
        // Fall back to live capture
        await handleCapture();
      }
    } catch {
      await handleCapture();
    } finally {
      setLoading(false);
    }
  }, [handleCapture, onCapture]);

  return (
    <div
      className={`rounded-xl border border-white/[0.06] bg-[#0d0d12] overflow-hidden ${className}`}
      style={{ boxShadow: "inset 0 1px 0 rgba(255,255,255,0.04)" }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06] bg-white/[0.02]">
        <Eye className="w-3.5 h-3.5 text-violet-400" />
        <span className="text-[12px] font-medium text-slate-300">Agent Vision</span>

        {capturedAt && (
          <span className="ml-2 flex items-center gap-1 text-[10px] text-slate-500">
            <Clock className="w-2.5 h-2.5" />
            {capturedAt.toLocaleTimeString()}
          </span>
        )}

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={loading}
            title="Load latest screenshot"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-white/[0.06] transition-all disabled:opacity-40"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={handleCapture}
            disabled={loading}
            title="Capture screen now"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600/20 border border-violet-500/30 text-violet-300 text-[11px] font-medium hover:bg-violet-600/30 transition-all disabled:opacity-40"
          >
            <Camera className="w-3 h-3" />
            Capture
          </button>
        </div>
      </div>

      {/* Image area */}
      <div className="relative aspect-video bg-[#080810] flex items-center justify-center">
        {activeUrl ? (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={activeUrl}
              alt="Agent screen capture"
              className="w-full h-full object-contain"
              onError={() => {
                setLocalUrl(null);
                setError("Failed to load screenshot");
              }}
            />
            {/* Scan line overlay for style */}
            <div className="absolute inset-0 pointer-events-none"
              style={{
                background: "linear-gradient(to bottom, transparent 97%, rgba(124,80,255,0.15) 100%)",
              }}
            />
          </>
        ) : (
          <div className="flex flex-col items-center gap-3 py-8">
            <div className="w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center">
              <Camera className="w-5 h-5 text-slate-600" />
            </div>
            <div className="text-center">
              <p className="text-[13px] text-slate-500 font-medium">No screenshot yet</p>
              <p className="text-[11px] text-slate-600 mt-0.5">Click Capture to see the agent&apos;s view</p>
            </div>
          </div>
        )}

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center backdrop-blur-sm">
            <div className="flex flex-col items-center gap-2">
              <RefreshCw className="w-5 h-5 text-violet-400 animate-spin" />
              <span className="text-[11px] text-violet-300">Capturing...</span>
            </div>
          </div>
        )}
      </div>

      {/* Error bar */}
      {error && (
        <div className="px-4 py-2 bg-red-500/10 border-t border-red-500/20 text-[11px] text-red-400">
          {error}
        </div>
      )}
    </div>
  );
}
