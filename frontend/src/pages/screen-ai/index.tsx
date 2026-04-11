"use client";
import { useState, useEffect, useRef } from "react";
import { Camera, Zap, RefreshCw, ChevronDown, CheckCircle, AlertTriangle, Eye, AlertCircle, Activity } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { analyseScreen, captureScreen, type ScreenAnalyseResponse } from "@/lib/api";

type ScanState = "idle" | "scanning" | "result" | "error" | "monitoring";

const ScreenAI = () => {
  const [scanState, setScanState] = useState<ScanState>("idle");
  const [result, setResult] = useState<ScreenAnalyseResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [showExplain, setShowExplain] = useState(false);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [isLiveMonitoring, setIsLiveMonitoring] = useState(false);
  const [monitoringStatus, setMonitoringStatus] = useState("Monitoring screen in background...");
  
  const wsRef = useRef<WebSocket | null>(null);
  const livePreviewInterval = useRef<NodeJS.Timeout | null>(null);

  // Poll screen just for UI preview when monitoring
  useEffect(() => {
    if (isLiveMonitoring) {
      livePreviewInterval.current = setInterval(async () => {
        try {
          const data = await captureScreen();
          if (data.image_base64) {
            setPreviewSrc(`data:image/png;base64,${data.image_base64}`);
          }
        } catch (e) {
          // ignore preview errors
        }
      }, 5000);
    } else {
      if (livePreviewInterval.current) clearInterval(livePreviewInterval.current);
    }
    return () => {
      if (livePreviewInterval.current) clearInterval(livePreviewInterval.current);
    };
  }, [isLiveMonitoring]);

  const toggleLiveMonitoring = () => {
    if (isLiveMonitoring) {
      // Turn off
      wsRef.current?.close();
      wsRef.current = null;
      setIsLiveMonitoring(false);
      setScanState("idle");
    } else {
      // Turn on
      const wsUrl = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(/^http/, 'ws') + "/api/screen/live-insights";
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        setIsLiveMonitoring(true);
        setScanState("monitoring");
        setResult(null);
        setError("");
        setShowExplain(false);
        setMonitoringStatus("Monitoring screen in background...");
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "status") {
            setMonitoringStatus(data.message);
            // Flash scanning state briefly for UI feedback
            setScanState("scanning");
          } else if (data.type === "insight") {
            setScanState("result");
            setResult({
              screen_text: data.error_text,
              analysis: data.analysis,
            });
            setShowExplain(true); // Auto-open explanation
          }
        } catch (e) {
          console.error("WS Parse error", e);
        }
      };
      
      ws.onerror = () => {
        setError("Failed to connect to live monitoring service");
        setScanState("error");
        setIsLiveMonitoring(false);
      };
      
      ws.onclose = () => {
        setIsLiveMonitoring(false);
        if (scanState === "monitoring") setScanState("idle");
      };
      
      wsRef.current = ws;
    }
  };

  const handleCapture = async () => {
    if (isLiveMonitoring) return;
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
            AI sees and understands your screen
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
            onClick={toggleLiveMonitoring}
            className={cn(
               "flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition-all border",
               isLiveMonitoring 
                ? "bg-warning/20 border-warning text-warning hover:bg-warning/30" 
                : "bg-card border-border text-foreground hover:bg-accent"
            )}
            style={isLiveMonitoring ? { boxShadow: "0 0 14px rgba(255,184,76,0.3)" } : {}}
          >
            <Activity className={cn("w-3.5 h-3.5", isLiveMonitoring && "animate-pulse")} /> 
            {isLiveMonitoring ? "Stop Live Monitoring" : "Live Monitoring"}
          </button>

          <button
            onClick={handleCapture}
            disabled={scanState === "scanning" || isLiveMonitoring}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-[13px] font-medium hover:bg-primary/90 transition-all disabled:opacity-60"
            style={!isLiveMonitoring ? { boxShadow: "0 0 14px rgba(124,80,255,0.3)" } : {}}
          >
            {scanState === "scanning" && !isLiveMonitoring ? (
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
            <div className={cn(
              "bg-card border rounded-xl overflow-hidden flex-1 transition-all",
              isLiveMonitoring ? "border-warning/50 ring-1 ring-warning/30" : "border-border"
            )}>
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
                {scanState === "scanning" && !isLiveMonitoring ? (
                  <div className="flex flex-col items-center justify-center gap-3">
                    <RefreshCw className="w-8 h-8 text-primary animate-spin" />
                    <p className="text-[12px] text-muted-foreground">Capturing screen...</p>
                  </div>
                ) : previewSrc ? (
                  // Real screenshot from backend
                  <div className="relative w-full h-full flex items-center justify-center bg-black/10">
                    <img
                      src={previewSrc}
                      alt="Screen capture"
                      className="w-full h-full object-contain max-h-[220px]"
                    />
                    {isLiveMonitoring && scanState === "scanning" && (
                       <div className="absolute inset-0 bg-primary/10 animate-pulse-ring flex items-center justify-center">
                          <Badge className="bg-primary/90 text-white border-0 shadow-lg">Analysing Error...</Badge>
                       </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center gap-3 py-8 text-center px-4">
                    <Camera className="w-10 h-10 text-muted-foreground/40" />
                    <p className="text-[13px] text-muted-foreground">
                      {isLiveMonitoring ? "Waiting for screen preview..." : "Click Capture now to analyse your screen"}
                    </p>
                  </div>
                )}
              </div>

              {/* OCR Text / Status */}
              <div className="px-5 py-4">
                <p className="text-[11px] text-muted-foreground mb-2">
                   {isLiveMonitoring && scanState !== "result" ? "Live Status:" : "Extracted text (OCR):"}
                </p>
                <div className="bg-secondary rounded-lg p-3 font-mono text-[11px] border border-border max-h-28 overflow-y-auto min-h-[4rem]">
                  {scanState === "monitoring" || (isLiveMonitoring && scanState === "scanning") ? (
                    <div className="flex items-center gap-3 h-full">
                       <span className="relative flex h-2.5 w-2.5">
                         <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-warning opacity-75"></span>
                         <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-warning"></span>
                       </span>
                       <p className="text-warning-foreground font-medium">{monitoringStatus}</p>
                    </div>
                  ) : scanState === "scanning" && !isLiveMonitoring ? (
                    <p className="text-muted-foreground animate-pulse">Reading screen content...</p>
                  ) : result ? (
                    <p className="text-foreground whitespace-pre-wrap">{result.screen_text}</p>
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
            <div className="bg-card border border-border rounded-xl overflow-hidden flex-1 flex flex-col">
              <div className="px-5 py-3.5 border-b border-border flex items-center gap-2">
                <Zap className={cn("w-4 h-4", isLiveMonitoring ? "text-warning" : "text-primary")} />
                <h2 className="text-[13px] font-semibold text-foreground">AI Insight</h2>
                <span className="text-[10px] text-muted-foreground ml-auto">qwen2.5-coder:7b</span>
              </div>

              <div className="px-5 py-5 space-y-4 flex-1 overflow-y-auto">
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
                      AI is analysing the screen...
                    </p>
                  </div>
                )}

                {scanState === "error" && !isLiveMonitoring && (
                  <div className="bg-destructive/10 border border-destructive/25 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertCircle className="w-4 h-4 text-destructive" />
                      <p className="text-[13px] font-semibold text-destructive">Capture failed</p>
                    </div>
                    <p className="text-[12px] text-muted-foreground leading-relaxed">{error}</p>
                  </div>
                )}

                {scanState === "monitoring" && (
                   <div className="flex flex-col items-center justify-center h-full gap-4 text-center opacity-70">
                      <Activity className="w-12 h-12 text-warning animate-pulse" />
                      <div>
                         <p className="text-[13px] font-semibold text-foreground">Monitoring for errors...</p>
                         <p className="text-[11px] text-muted-foreground mt-1 max-w-[200px]">
                            When an error appears on your screen, AI will auto-detect it and provide an explanation here.
                         </p>
                      </div>
                   </div>
                )}

                {scanState === "result" && result && (
                  <>
                    {/* Error/insight card */}
                    <div
                      className={cn(
                        "border rounded-xl p-4 transition-all duration-500",
                        hasError
                          ? "bg-destructive/10 border-destructive/25 shadow-[0_0_20px_rgba(239,68,68,0.15)]"
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
                          {hasError ? "Error detected on screen" : "Screen analysed"}
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
                      <div className="bg-secondary/40 rounded-xl px-4 py-4 border border-border text-[13px] leading-relaxed animate-fade-slide-up">
                        <p className="text-foreground font-semibold mb-3 flex items-center gap-2">
                           <Zap className="w-3.5 h-3.5 text-primary" /> AI Diagnosis:
                        </p>
                        <div className="text-muted-foreground whitespace-pre-wrap font-sans">
                           {result.analysis}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {scanState === "idle" && (
                  <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
                    <Camera className="w-10 h-10 text-muted-foreground/40" />
                    <p className="text-[13px] text-muted-foreground">
                      Capture a screenshot to get AI insights, or enable Live Monitoring
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
