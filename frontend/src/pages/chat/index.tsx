"use client";
import { useState, useEffect, useRef } from "react";
import { Send, Mic, Terminal, MoreHorizontal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface Message {
  id: number;
  role: "user" | "ai";
  content: string;
  success?: string;
  timestamp: string;
  typing?: boolean;
}

const getTime = () => new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

const initialMessages: Message[] = [
  { id: 1, role: "ai", content: "Hello Vamsee! I'm your AI assistant. How can I help you today?", timestamp: "08:00 AM" },
  { id: 2, role: "user", content: "Open VS Code", timestamp: "08:01 AM" },
  { id: 3, role: "ai", content: "Opening VS Code now...", success: "✓ VS Code launched successfully.", timestamp: "08:01 AM" },
  { id: 4, role: "user", content: "Organise my downloads folder", timestamp: "08:03 AM" },
  { id: 5, role: "ai", content: "Scanning Downloads folder... Found 18 files.", success: "✓ Organised into 4 categories: Images (7), Documents (5), Videos (3), Software (3).", timestamp: "08:03 AM" },
];

const aiReplies = [
  (cmd: string) => ({ content: `Processing "${cmd}"...`, success: "✓ Command executed successfully." }),
  () => ({ content: "Scanning your system for relevant files...", success: "✓ Found and organised 12 items." }),
  () => ({ content: "Understood. Executing on your PC...", success: "✓ Task completed." }),
];

const Chat = () => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = () => {
    if (!input.trim()) return;
    const userMsg: Message = { id: Date.now(), role: "user", content: input, timestamp: getTime() };
    setMessages((prev) => [...prev, userMsg]);
    const cmd = input;
    setInput("");

    setIsTyping(true);
    const delay = 800 + Math.random() * 600;
    setTimeout(() => {
      setIsTyping(false);
      const reply = aiReplies[Math.floor(Math.random() * aiReplies.length)](cmd);
      const aiMsg: Message = { id: Date.now() + 1, role: "ai", ...reply, timestamp: getTime() };
      setMessages((prev) => [...prev, aiMsg]);
    }, delay);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center">
            <Terminal className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-[13px] font-semibold text-foreground">Vamsee AI</h1>
            <p className="text-[10px] text-muted-foreground">Qwen2.5 · local model</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge className="bg-success/20 text-success border-0 text-[10px] px-2">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-status-pulse inline-block mr-1" />
            Online
          </Badge>
          <button className="w-7 h-7 rounded-md hover:bg-accent flex items-center justify-center transition-colors">
            <MoreHorizontal className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto px-6 py-5 space-y-5">
        {messages.map((msg) => (
          <div key={msg.id} className={cn("flex gap-3 animate-fade-slide-up", msg.role === "user" ? "justify-end" : "justify-start")}>
            {msg.role === "ai" && (
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center shrink-0 mt-0.5">
                <Terminal className="w-3.5 h-3.5 text-white" />
              </div>
            )}
            <div className="max-w-[68%]">
              <div
                className={cn(
                  "rounded-2xl px-4 py-3 text-[13px] leading-relaxed",
                  msg.role === "user"
                    ? "bg-primary/20 text-foreground border border-primary/20 rounded-tr-sm"
                    : "bg-card text-foreground border border-border rounded-tl-sm"
                )}
              >
                <p>{msg.content}</p>
                {msg.success && (
                  <p className="text-success mt-1.5 text-[12px]">{msg.success}</p>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground mt-1 px-1">{msg.timestamp}</p>
            </div>
            {msg.role === "user" && (
              <div className="w-7 h-7 rounded-lg bg-secondary border border-border flex items-center justify-center shrink-0 mt-0.5 text-[10px] font-bold text-foreground">
                V
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex gap-3 items-start animate-fade-slide-up">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center shrink-0">
              <Terminal className="w-3.5 h-3.5 text-white" />
            </div>
            <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex items-center gap-1.5 h-4">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-typing-dot"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="px-6 py-4 border-t border-border shrink-0">
        <div className="flex gap-2 items-center bg-card border border-border rounded-xl px-4 py-2 focus-within:border-primary/50 transition-colors">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Type a command or ask anything..."
            className="flex-1 bg-transparent text-[13px] text-foreground outline-none placeholder:text-muted-foreground"
          />
          <button className="p-1.5 rounded-lg hover:bg-accent transition-colors">
            <Mic className="w-4 h-4 text-muted-foreground" />
          </button>
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center hover:bg-primary/90 transition-colors disabled:opacity-40"
          >
            <Send className="w-3.5 h-3.5 text-primary-foreground" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chat;
