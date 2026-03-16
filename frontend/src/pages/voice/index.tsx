"use client";
import { useState, useCallback } from "react";
import { Mic, MicOff, Monitor, Clipboard, StopCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type VoiceState = "idle" | "listening" | "processing" | "speaking";

const quickCommands = ["Open VS Code", "Organise downloads", "Set a reminder", "Analyse screen", "Check tasks"];

const stateConfig: Record<VoiceState, { label: string; color: string; waveAnim: string }> = {
  idle: { label: "Click mic to start", color: "text-muted-foreground", waveAnim: "animate-waveform-idle" },
  listening: { label: "Listening...", color: "text-primary glow-text-primary", waveAnim: "animate-waveform" },
  processing: { label: "Processing...", color: "text-warning", waveAnim: "animate-waveform-idle" },
  speaking: { label: "Speaking...", color: "text-success", waveAnim: "animate-waveform" },
};

const statusMessages: Record<VoiceState, string> = {
  idle: "Say something or click a quick command below.",
  listening: "Speak now — I'm listening...",
  processing: "Understanding your request...",
  speaking: 'Opening VS Code now... ✓ VS Code launched successfully.',
};

const VoiceAssistant = () => {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [lastCommand, setLastCommand] = useState<string>("");
  const [log, setLog] = useState<string[]>([]);
  const [activeCmd, setActiveCmd] = useState<string | null>(null);

  const handleMic = useCallback(() => {
    if (voiceState === "idle") {
      setVoiceState("listening");
    } else if (voiceState === "listening") {
      setVoiceState("processing");
      setTimeout(() => {
        setVoiceState("speaking");
        setTimeout(() => setVoiceState("idle"), 3000);
      }, 1200);
    } else if (voiceState === "speaking" || voiceState === "processing") {
      setVoiceState("idle");
    }
  }, [voiceState]);

  const handleQuickCommand = (cmd: string) => {
    setActiveCmd(cmd);
    setLastCommand(cmd);
    setVoiceState("processing");
    setLog((prev) => [`> ${cmd}`, ...prev]);
    setTimeout(() => {
      setVoiceState("speaking");
      setLog((prev) => [`✓ ${cmd} executed successfully.`, ...prev]);
      setTimeout(() => {
        setVoiceState("idle");
        setActiveCmd(null);
      }, 2500);
    }, 1000);
  };

  const cfg = stateConfig[voiceState];
  const barCount = 28;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border shrink-0">
        <h1 className="text-base font-semibold text-foreground">Voice Assistant</h1>
        <p className="text-xs text-muted-foreground mt-0.5">Speak to control your PC · Qwen2.5 local</p>
      </div>

      {/* Main area */}
      <div className="flex-1 flex flex-col items-center justify-center gap-8 px-8 overflow-auto">
        {/* Status label */}
        <p className={cn("text-sm font-semibold tracking-wide transition-all duration-300", cfg.color)}>
          {cfg.label}
        </p>

        {/* Waveform visualizer */}
        <div className="flex items-center gap-[3px] h-16 px-4">
          {Array.from({ length: barCount }).map((_, i) => (
            <div
              key={i}
              className={cn(
                "w-[3px] rounded-full transition-colors duration-300",
                voiceState === "idle" ? "bg-border" : voiceState === "processing" ? "bg-warning/60" : "bg-primary",
                cfg.waveAnim
              )}
              style={{
                animationDelay: `${i * 0.04}s`,
                height: voiceState === "idle" ? "6px" : `${6 + Math.abs(Math.sin(i * 0.45)) * 38}px`,
              }}
            />
          ))}
        </div>

        {/* Mic button */}
        <div className="relative flex items-center justify-center">
          {(voiceState === "listening" || voiceState === "speaking") && (
            <div className="absolute w-24 h-24 rounded-full border-2 border-primary/30 animate-pulse-ring" />
          )}
          <button
            onClick={handleMic}
            className={cn(
              "relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-200 shadow-lg",
              voiceState === "idle"
                ? "bg-card border-2 border-border hover:border-primary/60 hover:bg-accent"
                : voiceState === "listening"
                ? "bg-primary border-2 border-primary"
                : voiceState === "processing"
                ? "bg-warning/20 border-2 border-warning"
                : "bg-success/20 border-2 border-success"
            )}
            style={voiceState !== "idle" ? { boxShadow: "0 0 32px rgba(124,80,255,0.4)" } : {}}
          >
            {voiceState === "idle" && <Mic className="w-7 h-7 text-muted-foreground" />}
            {voiceState === "listening" && <Mic className="w-7 h-7 text-white" />}
            {voiceState === "processing" && <StopCircle className="w-7 h-7 text-warning" />}
            {voiceState === "speaking" && <MicOff className="w-7 h-7 text-success" />}
          </button>
        </div>

        {/* Status card */}
        <div className="w-full max-w-lg bg-card border border-border rounded-xl px-5 py-4 min-h-[56px] transition-all duration-300">
          {lastCommand && voiceState !== "idle" ? (
            <div>
              <p className="text-[11px] text-muted-foreground mb-1">Command: <span className="text-foreground font-medium">{lastCommand}</span></p>
              <p className="text-sm text-foreground">{statusMessages[voiceState]}</p>
            </div>
          ) : (
            <p className="text-[13px] text-muted-foreground">{statusMessages[voiceState]}</p>
          )}
        </div>

        {/* Quick commands */}
        <div className="flex flex-wrap gap-2.5 justify-center">
          {quickCommands.map((cmd) => (
            <button
              key={cmd}
              onClick={() => handleQuickCommand(cmd)}
              disabled={voiceState === "processing" || voiceState === "listening"}
              className={cn(
                "px-4 py-2 rounded-full border text-[13px] transition-all duration-150 font-medium",
                activeCmd === cmd
                  ? "bg-primary border-primary text-white"
                  : "bg-card border-border text-foreground hover:border-primary/60 hover:bg-primary/10 disabled:opacity-40"
              )}
            >
              {cmd}
            </button>
          ))}
        </div>

        {/* Activity log */}
        {log.length > 0 && (
          <div className="w-full max-w-lg">
            <p className="text-[11px] text-muted-foreground mb-2">Command log</p>
            <div className="bg-card border border-border rounded-xl overflow-hidden max-h-32 overflow-y-auto">
              {log.map((entry, i) => (
                <div key={i} className="px-4 py-2 text-[12px] border-b border-border/50 last:border-b-0 font-mono
                  text-muted-foreground first:text-success">
                  {entry}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Helper buttons */}
        <div className="flex items-center gap-4 pb-4">
          <button className="w-10 h-10 rounded-full bg-card border border-border flex items-center justify-center hover:bg-accent transition-colors">
            <Monitor className="w-4 h-4 text-muted-foreground" />
          </button>
          <button className="w-10 h-10 rounded-full bg-card border border-border flex items-center justify-center hover:bg-accent transition-colors">
            <Clipboard className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default VoiceAssistant;
