"use client";
import { useState } from "react";
import { Camera, Zap, RefreshCw, ChevronDown, CheckCircle, AlertTriangle, Eye, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { analyseScreen, type ScreenAnalyseResponse } from "@/lib/api";

type ScanState = "idle" | "scanning" | "result" | "error";

const ScreenAI = () => {
  const [scanState, setScanState] = useState<ScanState>("idle");
  const [result, setResult] = useState<ScreenAnalyseResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [showExplain, setShowExplain] = useState(false);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);

  const handleCapture = async () => {
    setScanState("scanning");
    setError("");
    setShowExplain(false);
    setResult(null);

    try {
      const data = await analyseScreen();
      setResult(data);
      if (data.image_base64) {
        setPreviewSrc(`data:image/png;base64,${data.image_base64}`);
      }
      setScanState("result");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Screen capture failed";
      setError(msg);
      setScanState("error");
    }
  };

  // Detect if text looks like an error
  const hasError =
    result &&
    /error|exception|traceback|undefined|null|failed|crash/i.test(result.screen_text);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-base font-semibold text-foreground">Screen AI</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            AI sees and understands your screen in real time
          </p>
        </div>
        <div className="flex items-center gap-3">
          {scanState === "result" && (
            <Badge className="bg-success/20 text-success border-0 text-[11px] px-2.5 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-status-pulse inline-block mr-1.5" />
              Analysis ready
            </Badge>
          )}
          <button
            onClick={handleCapture}
            disabled={scanState === "scanning"}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-[13px] font-medium hover:bg-primary/90 transition-all disabled:opacity-60"
            style={{ boxShadow: "0 0 14px rgba(124,80,255,0.3)" }}
          >
            {scanState === "scanning" ? (
              <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Scanning...</>
            ) : (
              <><Camera className="w-3.5 h-3.5" /> Capture now</>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto px-8 py-6">
        <div className="grid grid-cols-2 gap-5 h-full">
          {/* Left: Live Capture Preview */}
          <div className="flex flex-col gap-4">
            <div className="bg-card border border-border rounded-xl overflow-hidden flex-1">
              <div className="px-5 py-3.5 border-b border-border flex items-center justify-between">
                <h2 className="text-[13px] font-semibold text-foreground">Live capture</h2>
                <div className="flex items-center gap-2">
                  <Eye className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="text-[11px] text-muted-foreground">Desktop</span>
                </div>
              </div>

              {/* Screen preview area */}
              <div
                className={cn(
                  "relative flex items-center justify-center bg-secondary/60 border-b border-border transition-all duration-300",
                  "min-h-[220px]"
                )}
              >
                {scanState === "scanning" ? (
                  <div className="flex flex-col items-center justify-center gap-3">
                    <RefreshCw className="w-8 h-8 text-primary animate-spin" />
                    <p className="text-[12px] text-muted-foreground">Capturing screen...</p>
                  </div>
                ) : previewSrc ? (
                  // Real screenshot from backend
                  <img
                    src={previewSrc}
                    alt="Screen capture"
                    className="w-full h-full object-contain max-h-[220px]"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center gap-3 py-8 text-center px-4">
                    <Camera className="w-10 h-10 text-muted-foreground/40" />
                    <p className="text-[13px] text-muted-foreground">
                      Click <strong>Capture now</strong> to analyse your screen
                    </p>
                    <p className="text-[11px] text-muted-foreground/60">
                      Requires Tesseract OCR to be installed
                    </p>
                  </div>
                )}
              </div>

              {/* OCR Text */}
              <div className="px-5 py-4">
                <p className="text-[11px] text-muted-foreground mb-2">Extracted text (OCR):</p>
                <div className="bg-secondary rounded-lg p-3 font-mono text-[11px] border border-border max-h-28 overflow-y-auto">
                  {scanState === "scanning" ? (
                    <p className="text-muted-foreground animate-pulse">Reading screen content...</p>
                  ) : result ? (
                    <p className="text-foreground whitespace-pre-wrap">{result.screen_text.slice(0, 400)}</p>
                  ) : scanState === "error" ? (
                    <p className="text-destructive">{error}</p>
                  ) : (
                    <p className="text-muted-foreground">No capture yet.</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right: AI Insight */}
          <div className="flex flex-col gap-4">
            <div className="bg-card border border-border rounded-xl overflow-hidden flex-1">
              <div className="px-5 py-3.5 border-b border-border flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                <h2 className="text-[13px] font-semibold text-foreground">AI Insight</h2>
                <span className="text-[10px] text-muted-foreground ml-auto">qwen2.5-coder:7b</span>
              </div>

              <div className="px-5 py-5 space-y-4">
                {scanState === "scanning" && (
                  <div className="space-y-3">
                    {[...Array(3)].map((_, i) => (
                      <div
                        key={i}
                        className="h-12 bg-secondary/60 rounded-lg animate-pulse"
                        style={{ animationDelay: `${i * 0.1}s` }}
                      />
                    ))}
                    <p className="text-[11px] text-muted-foreground text-center animate-pulse">
                      AI is analysing your screen...
                    </p>
                  </div>
                )}

                {scanState === "error" && (
                  <div className="bg-destructive/10 border border-destructive/25 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertCircle className="w-4 h-4 text-destructive" />
                      <p className="text-[13px] font-semibold text-destructive">Capture failed</p>
                    </div>
                    <p className="text-[12px] text-muted-foreground leading-relaxed">{error}</p>
                    <p className="text-[11px] text-muted-foreground mt-2">
                      Make sure <code className="text-foreground bg-secondary px-1 rounded">mss</code>,{" "}
                      <code className="text-foreground bg-secondary px-1 rounded">pytesseract</code>, and{" "}
                      <strong>Tesseract OCR</strong> are installed.
                    </p>
                  </div>
                )}

                {scanState === "result" && result && (
                  <>
                    {/* Error/insight card */}
                    <div
                      className={cn(
                        "border rounded-xl p-4",
                        hasError
                          ? "bg-destructive/10 border-destructive/25"
                          : "bg-primary/5 border-primary/20"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        {hasError ? (
                          <AlertTriangle className="w-4 h-4 text-destructive" />
                        ) : (
                          <CheckCircle className="w-4 h-4 text-success" />
                        )}
                        <p
                          className={cn(
                            "text-[13px] font-semibold",
                            hasError ? "text-destructive" : "text-success"
                          )}
                        >
                          {hasError ? "Issue detected" : "Screen analysed"}
                        </p>
                      </div>
                    </div>

                    {/* AI Analysis */}
                    <button
                      onClick={() => setShowExplain((v) => !v)}
                      className="w-full flex items-center justify-between px-4 py-3 bg-secondary/40 border border-border rounded-xl text-[13px] text-foreground hover:bg-accent/40 transition-colors"
                    >
                      <span>AI explanation</span>
                      <ChevronDown
                        className={cn(
                          "w-4 h-4 text-muted-foreground transition-transform",
                          showExplain && "rotate-180"
                        )}
                      />
                    </button>
                    {showExplain && (
                      <div className="bg-secondary/40 rounded-xl px-4 py-3.5 border border-border text-[12px] text-muted-foreground leading-relaxed animate-fade-slide-up max-h-64 overflow-y-auto">
                        <p className="text-foreground font-medium mb-2">AI says:</p>
                        <p className="whitespace-pre-wrap">{result.analysis}</p>
                      </div>
                    )}
                  </>
                )}

                {scanState === "idle" && (
                  <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
                    <Camera className="w-10 h-10 text-muted-foreground/40" />
                    <p className="text-[13px] text-muted-foreground">
                      Capture a screenshot to get AI insights
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScreenAI;
