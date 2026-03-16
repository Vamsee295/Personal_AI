"use client";
import { useState } from "react";
import { Camera, Zap, RefreshCw, ChevronDown, CheckCircle, AlertTriangle, Eye } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type ScanState = "idle" | "scanning" | "result";
type FixState = "idle" | "fixing" | "fixed";

const ScreenAI = () => {
  const [scanState, setScanState] = useState<ScanState>("result"); // start with result shown
  const [fixState, setFixState] = useState<FixState>("idle");
  const [showExplain, setShowExplain] = useState(false);

  const handleCapture = () => {
    setScanState("scanning");
    setFixState("idle");
    setShowExplain(false);
    setTimeout(() => setScanState("result"), 2500);
  };

  const handleFix = () => {
    setFixState("fixing");
    setTimeout(() => setFixState("fixed"), 1800);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-base font-semibold text-foreground">Screen AI</h1>
          <p className="text-xs text-muted-foreground mt-0.5">AI sees and understands your screen in real time</p>
        </div>
        <div className="flex items-center gap-3">
          {scanState === "result" && (
            <Badge className="bg-success/20 text-success border-0 text-[11px] px-2.5 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-status-pulse inline-block mr-1.5" />
              OCR scanning active
            </Badge>
          )}
          <button
            onClick={handleCapture}
            disabled={scanState === "scanning"}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-[13px] font-medium hover:bg-primary/90 transition-all disabled:opacity-60"
            style={{ boxShadow: "0 0 14px rgba(124,80,255,0.3)" }}
          >
            {scanState === "scanning"
              ? <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Scanning...</>
              : <><Camera className="w-3.5 h-3.5" /> Capture now</>
            }
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
              <div className={cn(
                "relative flex items-center justify-center bg-secondary/60 border-b border-border transition-all duration-300",
                "min-h-[220px]"
              )}>
                {scanState === "scanning" ? (
                  <div className="scan-overlay w-full h-full absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto mb-2" />
                      <p className="text-[12px] text-muted-foreground">Capturing screen...</p>
                    </div>
                  </div>
                ) : (
                  <div className="w-full h-full p-4 flex flex-col items-center justify-center gap-3">
                    {/* Simulated IDE screenshot */}
                    <div className="w-full max-w-xs bg-[#1e1e1e] rounded-lg p-3 font-mono text-[11px] border border-white/10">
                      <div className="flex gap-1.5 mb-3">
                        <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
                        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
                        <div className="w-2.5 h-2.5 rounded-full bg-green-500" />
                      </div>
                      <p className="text-blue-400">def <span className="text-yellow-400">calculate</span>():</p>
                      <p className="text-gray-300 pl-4">result = <span className="text-red-400">x</span> + 10</p>
                      <p className="text-gray-300 pl-4">return result</p>
                      <p className="text-red-400 mt-2 text-[10px]">NameError: name 'x' is not defined</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Last read text */}
              <div className="px-5 py-4">
                <p className="text-[11px] text-muted-foreground mb-2">Last read text:</p>
                <div className="bg-secondary rounded-lg p-3 font-mono text-[11px] border border-border">
                  {scanState === "scanning" ? (
                    <p className="text-muted-foreground animate-pulse">Reading screen content...</p>
                  ) : (
                    <>
                      <p className="text-destructive">NameError: name 'x' is not defined</p>
                      <p className="text-muted-foreground mt-1">File "main.py", line 12, in &lt;module&gt;</p>
                    </>
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
              </div>

              <div className="px-5 py-5 space-y-4">
                {scanState === "scanning" && (
                  <div className="space-y-3">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="h-12 bg-secondary/60 rounded-lg animate-pulse" style={{ animationDelay: `${i * 0.1}s` }} />
                    ))}
                  </div>
                )}

                {scanState === "result" && (
                  <>
                    {/* Error card */}
                    <div className="bg-destructive/10 border border-destructive/25 rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="w-4 h-4 text-destructive" />
                        <p className="text-[13px] font-semibold text-destructive">Error detected</p>
                      </div>
                      <p className="text-[12px] text-muted-foreground leading-relaxed">
                        A <code className="text-destructive bg-destructive/10 px-1 rounded">NameError</code> was detected on line 12. Variable{" "}
                        <code className="text-foreground bg-secondary px-1 rounded">x</code> is used before it is defined.
                      </p>
                    </div>

                    {/* Fix result */}
                    {fixState === "fixed" ? (
                      <div className="bg-success/10 border border-success/25 rounded-xl p-4 animate-fade-slide-up">
                        <div className="flex items-center gap-2 mb-2">
                          <CheckCircle className="w-4 h-4 text-success" />
                          <p className="text-[13px] font-semibold text-success">Fix applied</p>
                        </div>
                        <div className="font-mono text-[11px] bg-secondary rounded-lg p-3 border border-border space-y-1">
                          <p className="text-red-400 line-through opacity-60">result = x + 10</p>
                          <p className="text-green-400">x = 0  <span className="text-muted-foreground"># AI added: initialize x</span></p>
                          <p className="text-blue-300">result = x + 10</p>
                        </div>
                      </div>
                    ) : (
                      <div className="bg-secondary/60 border border-border rounded-xl p-4">
                        <p className="text-[13px] font-medium text-foreground mb-1.5">Suggestion</p>
                        <p className="text-[12px] text-muted-foreground leading-relaxed">
                          Define <code className="text-foreground bg-secondary px-1 rounded">x</code> before line 12, or verify the variable name for typos.
                        </p>
                      </div>
                    )}

                    {/* Explain accordion */}
                    <button
                      onClick={() => setShowExplain((v) => !v)}
                      className="w-full flex items-center justify-between px-4 py-3 bg-secondary/40 border border-border rounded-xl text-[13px] text-foreground hover:bg-accent/40 transition-colors"
                    >
                      <span>Explain error</span>
                      <ChevronDown className={cn("w-4 h-4 text-muted-foreground transition-transform", showExplain && "rotate-180")} />
                    </button>
                    {showExplain && (
                      <div className="bg-secondary/40 rounded-xl px-4 py-3.5 border border-border text-[12px] text-muted-foreground leading-relaxed animate-fade-slide-up">
                        <p className="text-foreground font-medium mb-2">What is a NameError?</p>
                        <p>Python raises a <code className="text-destructive">NameError</code> when you reference a variable name that hasn't been defined yet. In your code at line 12, <code className="text-foreground">x</code> is used in an expression before any value was assigned to it.</p>
                        <p className="mt-2">Common fixes:</p>
                        <ul className="mt-1 space-y-1 list-disc list-inside text-muted-foreground">
                          <li>Add <code className="text-foreground">x = 0</code> before line 12</li>
                          <li>Pass <code className="text-foreground">x</code> as a function parameter</li>
                          <li>Check for a typo — the variable may be named differently elsewhere</li>
                        </ul>
                      </div>
                    )}

                    {/* Action buttons */}
                    {fixState !== "fixed" && (
                      <div className="flex gap-3 pt-1">
                        <button
                          onClick={handleFix}
                          disabled={fixState === "fixing"}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-[13px] font-medium hover:bg-primary/90 transition-all disabled:opacity-60"
                          style={{ boxShadow: "0 0 14px rgba(124,80,255,0.3)" }}
                        >
                          {fixState === "fixing" ? (
                            <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Fixing...</>
                          ) : (
                            <>⚡ Fix it</>
                          )}
                        </button>
                      </div>
                    )}
                  </>
                )}

                {scanState === "idle" && (
                  <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
                    <Camera className="w-10 h-10 text-muted-foreground/40" />
                    <p className="text-[13px] text-muted-foreground">Capture a screenshot to get AI insights</p>
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
