"use client";
import { useState } from "react";
import { Send, Terminal, LayoutDashboard, Mic, MessageSquare, FolderOpen } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useRouter } from "next/router";

const quickCommands = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/" },
  { label: "Voice mode", icon: Mic, href: "/voice" },
  { label: "Chat", icon: MessageSquare, href: "/chat" },
  { label: "Organise files", icon: FolderOpen, href: "/files" },
];

export function FloatingBubble() {
  const [input, setInput] = useState("");
  const [open, setOpen] = useState(false);
  const router = useRouter();

  const handleSend = () => {
    if (!input.trim()) return;
    router.push(`/chat?q=${encodeURIComponent(input.trim())}`);
    setInput("");
    setOpen(false);
  };

  const handleCommand = (href: string) => {
    router.push(href);
    setOpen(false);
  };

  return (
    <div className="fixed bottom-5 right-5 z-50">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            className="relative w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200"
            style={{
              background: "linear-gradient(135deg, hsl(258,90%,60%), hsl(200,90%,55%))",
              boxShadow: open
                ? "0 0 32px rgba(124,80,255,0.7), 0 0 12px rgba(124,80,255,0.5)"
                : "0 0 18px rgba(124,80,255,0.4)",
            }}
          >
            <Terminal className="w-5 h-5 text-white" />
            {!open && (
              <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-destructive text-destructive-foreground text-[10px] flex items-center justify-center font-semibold">
                3
              </span>
            )}
            {/* Pulse ring */}
            <span
              className="absolute inset-0 rounded-full border-2 border-violet-400/40 animate-pulse-ring"
              style={{ animationDuration: "2.5s" }}
            />
          </button>
        </PopoverTrigger>

        <PopoverContent side="top" align="end" className="w-72 bg-card border border-border p-4 shadow-xl" style={{ boxShadow: "0 0 40px rgba(124,80,255,0.15), 0 8px 32px rgba(0,0,0,0.5)" }}>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center">
              <Terminal className="w-3.5 h-3.5 text-white" />
            </div>
            <p className="text-[12px] font-semibold text-foreground">Vamsee AI</p>
            <span className="ml-auto text-[10px] text-success flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-status-pulse inline-block" />
              Online
            </span>
          </div>

          {/* Quick nav */}
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Quick access</p>
          <div className="grid grid-cols-2 gap-1.5 mb-4">
            {quickCommands.map((cmd) => (
              <button
                key={cmd.label}
                onClick={() => handleCommand(cmd.href)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary hover:bg-accent border border-border text-[12px] text-foreground hover:border-primary/40 transition-all"
              >
                <cmd.icon className="w-3.5 h-3.5 text-primary" />
                {cmd.label}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="flex gap-2 items-center bg-secondary border border-border rounded-lg px-3 py-2 focus-within:border-primary/40 transition-colors">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask anything..."
              className="flex-1 bg-transparent text-[12px] text-foreground outline-none placeholder:text-muted-foreground"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="w-6 h-6 rounded-md bg-primary flex items-center justify-center hover:bg-primary/90 transition-colors disabled:opacity-40"
            >
              <Send className="w-3 h-3 text-primary-foreground" />
            </button>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
