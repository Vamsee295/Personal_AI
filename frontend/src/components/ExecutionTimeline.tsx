import React, { useEffect, useRef } from "react";
import { BrainEvent } from "@/hooks/useOrchestrator";
import { Brain, CheckCircle, XCircle, Globe, Search, ArrowRight, Activity, AlertTriangle, Play, RefreshCw, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

interface ExecutionTimelineProps {
  events: BrainEvent[];
  className?: string;
}

export function ExecutionTimeline({ events, className }: ExecutionTimelineProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const getEventIcon = (type: string, data: any) => {
    switch (type) {
      case "task_started": return <Play className="w-4 h-4 text-primary" />;
      case "planner_started": return <Brain className="w-4 h-4 text-purple-400" />;
      case "tool_selected":
      case "tool_started":
        if (data.tool === "search_web") return <Search className="w-4 h-4 text-blue-400" />;
        if (data.tool === "open_page") return <Globe className="w-4 h-4 text-blue-400" />;
        return <Activity className="w-4 h-4 text-blue-400" />;
      case "tool_finished":
        return data.success ? <CheckCircle className="w-4 h-4 text-green-400" /> : <XCircle className="w-4 h-4 text-red-400" />;
      case "observation_received": return <Layers className="w-4 h-4 text-orange-400" />;
      case "replanning_started": return <RefreshCw className="w-4 h-4 text-yellow-400 animate-spin-slow" />;
      case "task_completed": return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "task_failed": return <AlertTriangle className="w-5 h-5 text-red-500" />;
      case "agent_switched": return <ArrowRight className="w-4 h-4 text-indigo-400" />;
      default: return <Activity className="w-4 h-4 text-slate-400" />;
    }
  };

  const getEventText = (type: string, data: any) => {
    switch (type) {
      case "task_started": return `Task Started: ${data.command}`;
      case "planner_started": return "Planner is thinking...";
      case "planner_finished": return "Plan generated.";
      case "tool_selected": return `Selected Tool: ${data.tool}`;
      case "tool_started": return `Executing Tool: ${data.tool}`;
      case "tool_finished": return data.success ? `Tool succeeded: ${data.tool}` : `Tool failed: ${data.result}`;
      case "observation_received": return "Observation received from environment.";
      case "replanning_started": return `Replanning triggered. Reason: ${data.reason}`;
      case "task_completed": return `Task Completed: ${data.message}`;
      case "task_failed": return `Task Failed: ${data.error}`;
      case "agent_switched": return `Agent switched from ${data.old_agent} to ${data.new_agent}`;
      default: return `Unknown event: ${type}`;
    }
  };

  if (events.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center p-8 text-muted-foreground bg-black/20 rounded-lg border border-white/5", className)}>
        <Brain className="w-8 h-8 mb-3 opacity-20" />
        <p className="text-sm">No active execution</p>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col space-y-4 overflow-y-auto pr-2", className)}>
      {events.map((event, i) => {
        const isLast = i === events.length - 1;
        return (
          <div key={i} className="flex items-start group">
            <div className="flex flex-col items-center mr-4">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-white/5 border border-white/10 shrink-0">
                {getEventIcon(event.type, event.data)}
              </div>
              {!isLast && <div className="w-px h-full min-h-[1.5rem] bg-white/10 my-1"></div>}
            </div>
            <div className="flex flex-col pt-1 pb-2">
              <span className="text-xs font-mono text-muted-foreground mb-1">
                {new Date(event.timestamp * 1000).toLocaleTimeString()}
              </span>
              <span className={cn("text-sm",
                event.type === "task_failed" || (event.type === "tool_finished" && !event.data.success) ? "text-red-400" :
                event.type === "task_completed" ? "text-green-400 font-medium" : "text-foreground"
              )}>
                {getEventText(event.type, event.data)}
              </span>

              {/* Optional detailed JSON payload on hover for debugging */}
              {event.data && Object.keys(event.data).length > 0 && event.type !== 'task_started' && (
                <div className="mt-2 hidden group-hover:block max-w-full overflow-hidden">
                  <pre className="text-[10px] text-muted-foreground bg-black/30 p-2 rounded border border-white/5 whitespace-pre-wrap break-words">
                    {JSON.stringify(event.data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
