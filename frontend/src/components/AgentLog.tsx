import React, { useEffect, useRef } from "react";
import { Volume2 } from "lucide-react";

export type LogType = "info" | "action" | "success" | "error" | "system";

export interface LogEntry {
  id: string;
  timestamp: Date;
  type: LogType;
  message: string;
}

interface AgentLogProps {
  logs: LogEntry[];
  isRunning?: boolean;
  onSpeak?: (text: string) => void;
  className?: string;
}

function formatTime(d: Date): string {
  return d.toTimeString().slice(0, 8); // HH:MM:SS
}

const TYPE_STYLES: Record<LogType, { color: string; prefix: string; dot: string }> = {
  system:  { color: "text-slate-400",    prefix: "SYS", dot: "bg-slate-500" },
  info:    { color: "text-slate-300",    prefix: "INF", dot: "bg-slate-400" },
  action:  { color: "text-violet-400",   prefix: "ACT", dot: "bg-violet-500" },
  success: { color: "text-emerald-400",  prefix: "OK ", dot: "bg-emerald-500" },
  error:   { color: "text-red-400",      prefix: "ERR", dot: "bg-red-500" },
};

export default function AgentLog({ logs, isRunning = false, onSpeak, className = "" }: AgentLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom whenever new logs come in
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div
      className={`relative rounded-xl border border-white/[0.06] bg-[#0d0d12] overflow-hidden ${className}`}
      style={{ boxShadow: "inset 0 1px 0 rgba(255,255,255,0.04)" }}
    >
      {/* Terminal header bar */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
        <span className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
        <span className="w-2.5 h-2.5 rounded-full bg-amber-500/70" />
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
        <span className="ml-2 text-[11px] text-slate-500 font-mono">agent.log</span>
        {isRunning && (
          <span className="ml-auto flex items-center gap-1.5 text-[10px] text-violet-400 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
            running
          </span>
        )}
      </div>

      {/* Log body */}
      <div
        className="overflow-y-auto max-h-[300px] p-3 space-y-0.5 font-mono text-[12px] leading-relaxed"
        style={{ scrollbarWidth: "thin", scrollbarColor: "#2d2d3a transparent" }}
      >
        {logs.length === 0 && (
          <div className="text-slate-600 px-1 py-4 text-center">
            Waiting for commands...
          </div>
        )}

        {logs.map((log) => {
          const style = TYPE_STYLES[log.type] ?? TYPE_STYLES.info;
          return (
            <div
              key={log.id}
              className={`group flex items-start gap-2 px-1 py-[2px] rounded ${
                log.type === "error" ? "bg-red-500/5" :
                log.type === "success" ? "bg-emerald-500/5" :
                log.type === "action" ? "bg-violet-500/5" : ""
              }`}
            >
              {/* Timestamp */}
              <span className="text-slate-600 shrink-0 select-none">
                {formatTime(log.timestamp)}
              </span>

              {/* Type badge */}
              <span className={`shrink-0 text-[10px] font-bold ${style.color} opacity-70 select-none`}>
                [{style.prefix}]
              </span>

              {/* Message */}
              <span className={`${style.color} flex-1 break-all`}>
                {log.message}
              </span>

              {/* Speak button */}
              {onSpeak && (
                <button
                  onClick={() => onSpeak(log.message)}
                  className="p-1 rounded text-slate-600 hover:text-slate-300 hover:bg-white/5 opacity-0 group-hover:opacity-100 transition-all"
                  title="Speak log"
                >
                  <Volume2 className="w-2.5 h-2.5" />
                </button>
              )}
            </div>
          );
        })}

        {/* Blinking cursor while running */}
        {isRunning && (
          <div className="flex items-center gap-2 px-1 py-[2px]">
            <span className="text-slate-600 shrink-0 select-none">{formatTime(new Date())}</span>
            <span className="text-[10px] font-bold text-violet-400 opacity-70 select-none">[ACT]</span>
            <span className="text-violet-400">
              <span className="inline-block w-2 h-4 bg-violet-400 animate-pulse ml-0.5 align-middle" />
            </span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
