"use client";
import { useState } from "react";
import { Phone, ChevronDown, ChevronUp, PhoneIncoming } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

interface Call {
  id: number;
  name: string;
  initial: string;
  color: string;
  summary: string;
  time: string;
  duration: string;
  transcript: { speaker: string; text: string }[];
}

const initialCalls: Call[] = [
  {
    id: 1,
    name: "Rahul Sharma",
    initial: "RS",
    color: "from-purple-600 to-purple-500",
    summary: "Meeting moved to tomorrow. Will email details.",
    time: "14 min ago",
    duration: "2:34",
    transcript: [
      { speaker: "Rahul", text: "Hey, is Vamsee available?" },
      { speaker: "AI", text: "Hello sir, I am Vamsee's AI assistant. He is currently unavailable. How may I help you?" },
      { speaker: "Rahul", text: "Please tell him the meeting has been moved to tomorrow at 3 PM." },
      { speaker: "AI", text: "Understood. I'll inform Vamsee right away. Is there anything else?" },
      { speaker: "Rahul", text: "No that's all, thanks." },
      { speaker: "AI", text: "You're welcome. Have a good day!" },
    ],
  },
  {
    id: 2,
    name: "Priya Nair",
    initial: "PN",
    color: "from-pink-600 to-pink-500",
    summary: "Wants to schedule meeting tomorrow at 3 PM.",
    time: "1 hr ago",
    duration: "1:12",
    transcript: [
      { speaker: "Priya", text: "Can you check if Vamsee is free tomorrow at 3?" },
      { speaker: "AI", text: "Hello Priya, Vamsee is unavailable right now. I've noted your request for a meeting tomorrow at 3 PM." },
      { speaker: "Priya", text: "Great, thanks!" },
    ],
  },
  {
    id: 3,
    name: "Unknown Caller",
    initial: "?",
    color: "from-gray-600 to-gray-500",
    summary: "No message left. Call ended after greeting.",
    time: "3 hr ago",
    duration: "0:18",
    transcript: [
      { speaker: "AI", text: "Hello, I am Vamsee's AI assistant. He is currently unavailable. How may I assist you?" },
      { speaker: "Unknown", text: "..." },
    ],
  },
];

const CallLogs = () => {
  const [autoAnswer, setAutoAnswer] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);

  const toggleExpand = (id: number) => setExpanded((prev) => (prev === id ? null : id));

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-base font-semibold text-foreground">Call Logs</h1>
          <p className="text-xs text-muted-foreground mt-0.5">AI-answered calls & transcripts</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[13px] text-muted-foreground">Auto-answer</span>
          <Switch checked={autoAnswer} onCheckedChange={setAutoAnswer} />
          <Badge className={cn(
            "text-[10px] border-0 px-2",
            autoAnswer ? "bg-success/20 text-success" : "bg-muted text-muted-foreground"
          )}>
            {autoAnswer ? "● ON" : "OFF"}
          </Badge>
        </div>
      </div>

      {/* Stats bar */}
      <div className="px-8 py-3 border-b border-border/50 flex items-center gap-6 bg-card/30 shrink-0">
        <div className="flex items-center gap-2">
          <Phone className="w-3.5 h-3.5 text-primary" />
          <span className="text-[12px] text-muted-foreground"><span className="text-foreground font-medium">{initialCalls.length}</span> calls today</span>
        </div>
        <div className="flex items-center gap-2">
          <PhoneIncoming className="w-3.5 h-3.5 text-success" />
          <span className="text-[12px] text-muted-foreground"><span className="text-foreground font-medium">100%</span> auto-answered</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[12px] text-muted-foreground">Avg duration: <span className="text-foreground font-medium">1:21</span></span>
        </div>
      </div>

      {/* Call list */}
      <div className="flex-1 overflow-auto px-8 py-6 space-y-4">
        {initialCalls.map((c) => {
          const isOpen = expanded === c.id;
          return (
            <div
              key={c.id}
              className="bg-card border border-border rounded-xl overflow-hidden transition-all duration-200 hover:border-border/80"
            >
              {/* Call header */}
              <button
                className="w-full flex items-start gap-4 px-5 py-4 text-left hover:bg-accent/30 transition-colors"
                onClick={() => toggleExpand(c.id)}
              >
                <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${c.color} flex items-center justify-center text-[11px] font-bold text-white shrink-0`}>
                  {c.initial}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[13px] font-semibold text-foreground">{c.name}</span>
                    <span className="text-[11px] text-muted-foreground">{c.time}</span>
                  </div>
                  <p className="text-[12px] text-muted-foreground italic truncate">"{c.summary}"</p>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-[11px] text-muted-foreground">Duration: {c.duration}</span>
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-success/30 text-success">AI answered</Badge>
                  </div>
                </div>
                <div className="ml-2 mt-1">
                  {isOpen
                    ? <ChevronUp className="w-4 h-4 text-muted-foreground" />
                    : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
                </div>
              </button>

              {/* Transcript */}
              {isOpen && (
                <div className="border-t border-border bg-secondary/40 px-5 py-4 space-y-3">
                  <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-3">Transcript</p>
                  {c.transcript.map((line, i) => (
                    <div key={i} className={cn("flex gap-3", line.speaker === "AI" ? "justify-start" : "justify-end")}>
                      {line.speaker === "AI" && (
                        <div className="w-5 h-5 rounded-full bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center text-[8px] font-bold text-white shrink-0 mt-0.5">AI</div>
                      )}
                      <div className={cn(
                        "max-w-[75%] rounded-xl px-3 py-2 text-[12px] leading-relaxed",
                        line.speaker === "AI"
                          ? "bg-card border border-border text-foreground"
                          : "bg-primary/15 border border-primary/20 text-foreground"
                      )}>
                        <span className="text-[10px] font-semibold text-muted-foreground block mb-0.5">{line.speaker}</span>
                        {line.text}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CallLogs;
