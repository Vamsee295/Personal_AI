"use client";
import { useState, useEffect, useRef } from "react";
import { Send, Mic, Terminal, MoreHorizontal, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { chatStream, getHealth, type ChatMessage as APIChatMessage } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";

interface Message {
  id: number;
  role: "user" | "ai";
  content: string;
  timestamp: string;
  error?: boolean;
}

const getTime = () =>
  new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

const Chat = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      role: "ai",
      content: "Hello Vamsee! I'm Ultron, your AI assistant powered by **qwen2.5-coder:7b** running locally. How can I help you today?",
      timestamp: getTime(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [ollamaOnline, setOllamaOnline] = useState<boolean | null>(null);
  const [history, setHistory] = useState<APIChatMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Check Ollama health on mount
  useEffect(() => {
    getHealth()
      .then((h) => setOllamaOnline(h.ollama_running))
      .catch(() => setOllamaOnline(false));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;

    const userContent = input.trim();
    const userMsg: Message = { id: Date.now(), role: "user", content: userContent, timestamp: getTime() };
    const newHistory: APIChatMessage[] = [...history, { role: "user", content: userContent }];
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    // Create AI message placeholder for streaming
    const aiId = Date.now() + 1;
    setMessages((prev) => [...prev, { id: aiId, role: "ai", content: "", timestamp: getTime() }]);

    try {
      let fullResponse = "";

      for await (const token of chatStream(userContent, history, "qwen2.5-coder:7b")) {
        fullResponse += token;
        setMessages((prev) =>
          prev.map((m) => (m.id === aiId ? { ...m, content: fullResponse } : m))
        );
      }

      // Update history for next turn
      setHistory([...newHistory, { role: "assistant", content: fullResponse }]);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Connection failed. Is the backend running?";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiId ? { ...m, content: errorMsg, error: true } : m
        )
      );
    } finally {
      setIsTyping(false);
    }
  };

  const statusColor = ollamaOnline === null ? "text-muted-foreground" : ollamaOnline ? "text-success" : "text-destructive";
  const statusLabel = ollamaOnline === null ? "Checking..." : ollamaOnline ? "Online" : "Offline";
  const statusBg = ollamaOnline === null ? "bg-muted/20" : ollamaOnline ? "bg-success/20" : "bg-destructive/20";

  /**
   * Layer 2: Response Formatter Layer
   * Cleans AI response to fix common formatting issues before rendering.
   */
  /**
   * Cleans AI response to fix common formatting issues before rendering.
   */
  const formatAIResponse = (text: string) => {
    if (!text) return "";
    
    // Normalize line endings
    let processed = text.replace(/\r\n/g, '\n');

    // 1. Decouple glued backticks from preceding text
    processed = processed.replace(/([^\n])(`{1,3})/g, "$1\n\n$2");

    // 2. Fix known AI merged words failure modes
    processed = processed.replace(/javapublic/g, "java\npublic");
    
    // 3. Spacing fix for lists and segments
    processed = processed.replace(/([^\n])\n(\d+\.|\*|-)\s/g, "$1\n\n$2 ");
    processed = processed.replace(/\n{3,}/g, "\n\n");

    return processed;
  };

  /**
   * Parses the message into digestible segments of text and code blocks.
   */
  const renderMessageContent = (content: string) => {
    const cleaned = formatAIResponse(content);
    
    // Regex to find code blocks: ```[lang]\n[code]```
    // Also catches cases where backticks are glued or missing a newline
    const codeBlockRegex = /```(\w+)?\s*\n?([\s\S]*?)(?:```|$)/g;
    
    const parts: { type: "text" | "code"; content: string; lang?: string }[] = [];
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(cleaned)) !== null) {
      if (match.index > lastIndex) {
        parts.push({
          type: "text",
          content: cleaned.slice(lastIndex, match.index),
        });
      }

      let lang = match[1] || "plaintext";
      let code = match[2].trim();

      // Fix mangled content leaked backticks
      code = code.replace(/^`+/, "").replace(/`+$/, "").trim();

      // Handle the "javapublic" case in detected language
      if (lang.toLowerCase().startsWith("jav")) lang = "java";
      if (lang.toLowerCase().startsWith("js")) lang = "javascript";
      if (lang.toLowerCase().startsWith("ts")) lang = "typescript";
      if (lang.toLowerCase().startsWith("py")) lang = "python";

      parts.push({
        type: "code",
        lang,
        content: code,
      });

      lastIndex = codeBlockRegex.lastIndex;
    }

    if (lastIndex < cleaned.length) {
      parts.push({ type: "text", content: cleaned.slice(lastIndex) });
    }

    return (
      <div className="space-y-4">
        {parts.map((part, i) => (
          <div key={i}>
            {part.type === "code" ? (
              <div className="relative group my-4 rounded-xl overflow-hidden border border-white/10 bg-[#0d1117]">
                <div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/5">
                  <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                    {part.lang}
                  </span>
                  <button
                    className="text-[10px] text-muted-foreground hover:text-white transition-colors"
                    onClick={() => navigator.clipboard.writeText(part.content)}
                  >
                    Copy
                  </button>
                </div>
                <div className="p-4 overflow-x-auto text-[12.5px] font-mono">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                  >
                    {`\`\`\`${part.lang}\n${part.content}\n\`\`\``}
                  </ReactMarkdown>
                </div>
              </div>
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                  h1: ({ children }) => <h1 className="text-lg font-bold mt-4 mb-2 text-primary">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-bold mt-4 mb-2 text-primary/90">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-bold mt-3 mb-1">{children}</h3>,
                  p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc ml-4 mb-4 space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal ml-4 mb-4 space-y-1">{children}</ol>,
                  li: ({ children }) => <li className="pl-1">{children}</li>,
                  code: ({ node, inline, className, children, ...props }: any) => (
                    <code className="bg-primary/10 text-primary px-1.5 py-0.5 rounded font-mono text-[12px]" {...props}>
                      {children}
                    </code>
                  ),
                }}
              >
                {part.content}
              </ReactMarkdown>
            )}
          </div>
        ))}
      </div>
    );
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
            <h1 className="text-[13px] font-semibold text-foreground">Ultron</h1>
            <p className="text-[10px] text-muted-foreground">qwen2.5-coder:7b · local model</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge className={`${statusBg} ${statusColor} border-0 text-[10px] px-2`}>
            <span className={`w-1.5 h-1.5 rounded-full ${ollamaOnline ? "bg-success animate-status-pulse" : "bg-destructive"} inline-block mr-1`} />
            {statusLabel}
          </Badge>
          <button className="w-7 h-7 rounded-md hover:bg-accent flex items-center justify-center transition-colors">
            <MoreHorizontal className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      </div>

      {/* Offline warning */}
      {ollamaOnline === false && (
        <div className="mx-6 mt-3 bg-destructive/10 border border-destructive/30 rounded-lg px-4 py-2.5 flex items-center gap-2 text-[12px] text-destructive shrink-0">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          Ollama is not running. Start it with: <code className="font-mono bg-destructive/10 px-1 rounded">ollama serve</code>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-auto px-6 py-5 space-y-6">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn("flex gap-4 animate-fade-slide-up", msg.role === "user" ? "justify-end" : "justify-start")}
          >
            {msg.role === "ai" && (
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center shrink-0 mt-1 shadow-lg shadow-violet-500/20">
                <Terminal className="w-4 h-4 text-white" />
              </div>
            )}
            <div className="max-w-[85%] lg:max-w-[75%]">
              <div
                className={cn(
                  "rounded-2xl px-6 py-4 text-[13.5px] leading-relaxed",
                  msg.role === "user"
                    ? "bg-primary/20 text-foreground border border-primary/20 rounded-tr-sm whitespace-pre-wrap"
                    : msg.error
                    ? "bg-destructive/10 text-destructive border border-destructive/20 rounded-tl-sm whitespace-pre-wrap"
                    : "bg-card text-foreground border border-border rounded-tl-sm shadow-sm prose prose-sm prose-invert max-w-none"
                )}
              >
                {msg.content ? (
                  msg.role === "ai" && !msg.error ? (
                    renderMessageContent(msg.content)
                  ) : (
                    msg.content
                  )
                ) : (
                  <span className="flex items-center gap-1.5 h-4">
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-typing-dot"
                        style={{ animationDelay: `${i * 0.2}s` }}
                      />
                    ))}
                  </span>
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
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="px-6 py-4 border-t border-border shrink-0">
        <div className="flex gap-2 items-center bg-card border border-border rounded-xl px-4 py-2 focus-within:border-primary/50 transition-colors">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder={isTyping ? "AI is responding..." : "Type a command or ask anything..."}
            disabled={isTyping}
            className="flex-1 bg-transparent text-[13px] text-foreground outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
          />
          <button className="p-1.5 rounded-lg hover:bg-accent transition-colors">
            <Mic className="w-4 h-4 text-muted-foreground" />
          </button>
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center hover:bg-primary/90 transition-colors disabled:opacity-40"
          >
            <Send className="w-3.5 h-3.5 text-primary-foreground" />
          </button>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1.5 text-center">
          Powered by Ollama · qwen2.5-coder:7b running locally
        </p>
      </div>
    </div>
  );
};

export default Chat;
