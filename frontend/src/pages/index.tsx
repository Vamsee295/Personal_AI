"use client";
import { useState } from "react";
import { FolderSync, Image, FileText, Video, Package, RefreshCw, Check, FolderOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type OrgStatus = "idle" | "scanning" | "organising" | "done";

interface Category {
  key: string;
  Icon: React.ElementType;
  iconColor: string;
  bg: string;
  label: string;
  count: number;
  size: string;
  percent: number;
}

const categories: Category[] = [
  { key: "img", Icon: Image, iconColor: "text-blue-400", bg: "bg-blue-500/15", label: "Images", count: 32, size: "247 MB", percent: 45 },
  { key: "doc", Icon: FileText, iconColor: "text-red-400", bg: "bg-red-500/15", label: "Documents", count: 18, size: "38 MB", percent: 20 },
  { key: "vid", Icon: Video, iconColor: "text-purple-400", bg: "bg-purple-500/15", label: "Videos", count: 8, size: "1.2 GB", percent: 65 },
  { key: "sw", Icon: Package, iconColor: "text-amber-400", bg: "bg-amber-500/15", label: "Software", count: 5, size: "480 MB", percent: 35 },
];

const statusMessages: Record<OrgStatus, string> = {
  idle: "Downloads — ready to organise",
  scanning: "Scanning Downloads folder...",
  organising: "Moving files into folders...",
  done: "All done! 63 files organised into 4 folders.",
};

const Files = () => {
  const [status, setStatus] = useState<OrgStatus>("idle");

  const handleOrganise = () => {
    if (status === "done") { setStatus("idle"); return; }
    setStatus("scanning");
    setTimeout(() => {
      setStatus("organising");
      setTimeout(() => setStatus("done"), 1800);
    }, 1400);
  };

  const isRunning = status === "scanning" || status === "organising";

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-base font-semibold text-foreground">File Manager</h1>
          <p className="text-xs text-muted-foreground mt-0.5">AI-powered file organisation</p>
        </div>
        <button
          onClick={handleOrganise}
          disabled={isRunning}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition-all duration-200",
            status === "done"
              ? "bg-success/20 text-success border border-success/30 hover:bg-success/30"
              : "bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
          )}
          style={!isRunning && status !== "done" ? { boxShadow: "0 0 14px rgba(124,80,255,0.3)" } : {}}
        >
          {status === "done" ? (
            <><Check className="w-3.5 h-3.5" /> Done — Reset</>
          ) : isRunning ? (
            <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> {status === "scanning" ? "Scanning..." : "Organising..."}</>
          ) : (
            <><FolderSync className="w-3.5 h-3.5" /> Organise now</>
          )}
        </button>
      </div>

      {/* Status bar */}
      <div className={cn(
        "px-8 py-3 border-b border-border/50 flex items-center gap-3 shrink-0 transition-colors duration-300",
        status === "done" ? "bg-success/10" : "bg-card/30"
      )}>
        <FolderOpen className={cn("w-3.5 h-3.5", status === "done" ? "text-success" : "text-muted-foreground")} />
        <span className={cn("text-[12px]", status === "done" ? "text-success" : "text-muted-foreground")}>
          {statusMessages[status]}
        </span>
        {isRunning && (
          <div className="flex-1 bg-border rounded-full h-1 overflow-hidden max-w-xs ml-auto">
            <div className={cn(
              "h-full bg-primary rounded-full transition-all duration-[1800ms]",
              status === "organising" ? "w-full" : "w-1/3"
            )} />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto px-8 py-6 space-y-4">
        {/* Suggestion Banner */}
        {status === "idle" && (
          <div className="bg-primary/8 border border-primary/20 rounded-xl px-5 py-4 flex items-start gap-4 animate-fade-slide-up">
            <div className="w-9 h-9 rounded-lg bg-primary/15 flex items-center justify-center shrink-0">
              <FolderSync className="w-4 h-4 text-primary" />
            </div>
            <div>
              <p className="text-[13px] font-medium text-foreground mb-0.5">AI Suggestion</p>
              <p className="text-[12px] text-muted-foreground">63 files detected in Downloads. 4 categories found. Click <span className="text-primary font-medium">Organise now</span> to clean up.</p>
            </div>
          </div>
        )}

        {/* Category cards */}
        <div className="grid grid-cols-2 gap-4">
          {categories.map((c) => (
            <div
              key={c.key}
              className="bg-card border border-border rounded-xl p-5 hover:border-border/80 transition-colors"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className={`w-10 h-10 rounded-xl ${c.bg} flex items-center justify-center`}>
                  <c.Icon className={`w-5 h-5 ${c.iconColor}`} />
                </div>
                <div>
                  <p className="text-[13px] font-semibold text-foreground">{c.label}</p>
                  <p className="text-[11px] text-muted-foreground">{c.count} files · {c.size}</p>
                </div>
                {status === "done" && (
                  <Badge className="ml-auto text-[10px] bg-success/20 text-success border-0">Sorted</Badge>
                )}
              </div>
              {/* Progress bar */}
              <div className="bg-border rounded-full h-1.5 overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all duration-1000", c.iconColor.replace("text-", "bg-").replace("-400", "-500"))}
                  style={{ width: status === "idle" ? "0%" : `${c.percent}%`, transitionDelay: status !== "idle" ? "300ms" : "0ms" }}
                />
              </div>
              <p className="text-[10px] text-muted-foreground mt-1">{c.percent}% of Downloads</p>
            </div>
          ))}
        </div>

        {/* Folder tree preview */}
        {status === "done" && (
          <div className="bg-card border border-border rounded-xl p-5 animate-fade-slide-up">
            <p className="text-[12px] font-medium text-foreground mb-3">Folder structure</p>
            <div className="font-mono text-[12px] space-y-1.5 text-muted-foreground">
              <p className="text-foreground">📁 Downloads/</p>
              {categories.map((c) => (
                <p key={c.key} className="pl-4">├── 📁 {c.label}/ <span className="text-muted-foreground/60">({c.count} files)</span></p>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Files;
