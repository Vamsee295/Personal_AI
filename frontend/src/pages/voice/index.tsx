"use client";
import { useState, useCallback, useRef } from "react";
import { Mic, MicOff, Monitor, StopCircle, AlertCircle, Volume2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { voiceRespond } from "@/lib/api";

type VoiceState = "idle" | "listening" | "processing" | "speaking" | "error";

const quickCommands = [
  "Open VS Code",
  "Organise downloads",
  "What is Python?",
  "Analyse my screen",
  "Check the time",
];

const stateConfig: Record<VoiceState, { label: string; color: string }> = {
  idle:       { label: "Click mic to start",  color: "text-muted-foreground" },
  listening:  { label: "Listening...",          color: "text-primary" },
  processing: { label: "Processing...",         color: "text-warning" },
  speaking:   { label: "AI is responding...",   color: "text-success" },
  error:      { label: "Error occurred",        color: "text-destructive" },
};

interface LogEntry {
  type: "command" | "response" | "error";
  text: string;
  time: string;
}

const getTime = () =>
  new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

const VoiceAssistant = () => {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [lastCommand, setLastCommand] = useState("");
  const [lastResponse, setLastResponse] = useState("");
  const [log, setLog] = useState<LogEntry[]>([]);
  const [errorMsg, setErrorMsg] = useState("");
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const appendLog = (type: LogEntry["type"], text: string) =>
    setLog((prev) => [{ type, text, time: getTime() }, ...prev]);

  // ── Real speech recognition using browser Web Speech API ──────────
  const startListening = useCallback(() => {
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      setErrorMsg("Browser Speech Recognition not supported. Try Chrome or Edge.");
      setVoiceState("error");
      return;
    }

    const SpeechRecognitionAPI =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    const recognition: SpeechRecognition = new SpeechRecognitionAPI();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognitionRef.current = recognition;

    setVoiceState("listening");
    setLastCommand("");
    setErrorMsg("");

    recognition.onresult = async (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript;
      setLastCommand(transcript);
      appendLog("command", transcript);
      setVoiceState("processing");

      try {
        // Send transcript to backend AI
        const data = await voiceRespond(transcript, "qwen2.5-coder:7b", false);
        setLastResponse(data.ai_response);
        appendLog("response", data.ai_response);
        setVoiceState("speaking");

        // Browser TTS – speak the response
        if ("speechSynthesis" in window) {
          const utterance = new SpeechSynthesisUtterance(data.ai_response);
          utterance.rate = 0.95;
          utterance.pitch = 1.0;
          utterance.onend = () => setVoiceState("idle");
          speechSynthesis.speak(utterance);
        } else {
          setTimeout(() => setVoiceState("idle"), 3000);
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Backend error";
        setErrorMsg(msg);
        appendLog("error", msg);
        setVoiceState("error");
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const msg = `Mic error: ${event.error}`;
      setErrorMsg(msg);
      appendLog("error", msg);
      setVoiceState("error");
    };

    recognition.onend = () => {
      if (voiceState === "listening") setVoiceState("idle");
    };

    recognition.start();
  }, [voiceState]);

  const stopListening = () => {
    recognitionRef.current?.stop();
    speechSynthesis.cancel();
    setVoiceState("idle");
  };

  // ── Quick command (types text, sends directly to AI) ──────────────
  const handleQuickCommand = async (cmd: string) => {
    if (voiceState !== "idle") return;
    setLastCommand(cmd);
    appendLog("command", cmd);
    setVoiceState("processing");

    try {
      const data = await voiceRespond(cmd, "qwen2.5-coder:7b", false);
      setLastResponse(data.ai_response);
      appendLog("response", data.ai_response);
      setVoiceState("speaking");

      if ("speechSynthesis" in window) {
        const utterance = new SpeechSynthesisUtterance(data.ai_response);
        utterance.onend = () => setVoiceState("idle");
        speechSynthesis.speak(utterance);
      } else {
        setTimeout(() => setVoiceState("idle"), 2500);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Backend error";
      setErrorMsg(msg);
      appendLog("error", msg);
      setVoiceState("error");
    }
  };

  const handleMic = () => {
    if (voiceState === "idle") startListening();
    else stopListening();
  };

  const cfg = stateConfig[voiceState];
  const barCount = 28;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border shrink-0">
        <h1 className="text-base font-semibold text-foreground">Voice Assistant</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Speak to Vamsee AI · qwen2.5-coder:7b local model
        </p>
      </div>

      {/* Main area */}
      <div className="flex-1 flex flex-col items-center justify-center gap-6 px-8 overflow-auto py-6">

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
                "w-[3px] rounded-full transition-all duration-150",
                voiceState === "idle" || voiceState === "error"
                  ? "bg-border"
                  : voiceState === "processing"
                  ? "bg-warning/60"
                  : voiceState === "speaking"
                  ? "bg-success"
                  : "bg-primary"
              )}
              style={{
                height:
                  voiceState === "idle" || voiceState === "error"
                    ? "6px"
                    : `${6 + Math.abs(Math.sin(i * 0.45 + Date.now() * 0.001)) * 38}px`,
                transition: "height 0.15s ease",
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
              voiceState === "idle"   ? "bg-card border-2 border-border hover:border-primary/60 hover:bg-accent"
            : voiceState === "listening" ? "bg-primary border-2 border-primary"
            : voiceState === "processing" ? "bg-warning/20 border-2 border-warning"
            : voiceState === "speaking"   ? "bg-success/20 border-2 border-success"
            : "bg-destructive/20 border-2 border-destructive"
            )}
            style={voiceState !== "idle" && voiceState !== "error" ? { boxShadow: "0 0 32px rgba(124,80,255,0.4)" } : {}}
          >
            {voiceState === "idle"       && <Mic className="w-7 h-7 text-muted-foreground" />}
            {voiceState === "listening"  && <Mic className="w-7 h-7 text-white" />}
            {voiceState === "processing" && <StopCircle className="w-7 h-7 text-warning" />}
            {voiceState === "speaking"   && <Volume2 className="w-7 h-7 text-success" />}
            {voiceState === "error"      && <MicOff className="w-7 h-7 text-destructive" />}
          </button>
        </div>

        {/* Status / response card */}
        <div className="w-full max-w-lg bg-card border border-border rounded-xl px-5 py-4 space-y-2">
          {lastCommand && (
            <p className="text-[11px] text-muted-foreground">
              You said: <span className="text-foreground font-medium">"{lastCommand}"</span>
            </p>
          )}
          {lastResponse && voiceState === "speaking" && (
            <p className="text-[13px] text-foreground leading-relaxed">{lastResponse}</p>
          )}
          {voiceState === "error" && (
            <div className="flex items-center gap-2 text-destructive text-[12px]">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              {errorMsg || "Something went wrong"}
            </div>
          )}
          {!lastCommand && voiceState === "idle" && (
            <p className="text-[13px] text-muted-foreground">
              Say something or choose a quick command below.
            </p>
          )}
        </div>

        {/* Quick commands */}
        <div className="flex flex-wrap gap-2.5 justify-center">
          {quickCommands.map((cmd) => (
            <button
              key={cmd}
              onClick={() => handleQuickCommand(cmd)}
              disabled={voiceState !== "idle"}
              className={cn(
                "px-4 py-2 rounded-full border text-[13px] transition-all duration-150 font-medium",
                "bg-card border-border text-foreground hover:border-primary/60 hover:bg-primary/10 disabled:opacity-40"
              )}
            >
              {cmd}
            </button>
          ))}
        </div>

        {/* Activity log */}
        {log.length > 0 && (
          <div className="w-full max-w-lg">
            <p className="text-[11px] text-muted-foreground mb-2">Conversation log</p>
            <div className="bg-card border border-border rounded-xl overflow-hidden max-h-40 overflow-y-auto">
              {log.map((entry, i) => (
                <div
                  key={i}
                  className={cn(
                    "px-4 py-2 text-[12px] border-b border-border/50 last:border-b-0 font-mono",
                    entry.type === "command" ? "text-primary" : entry.type === "error" ? "text-destructive" : "text-muted-foreground"
                  )}
                >
                  <span className="text-[10px] opacity-50 mr-2">{entry.time}</span>
                  {entry.type === "command" ? `> ${entry.text}` : entry.type === "error" ? `✗ ${entry.text}` : `✓ ${entry.text.slice(0, 120)}`}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center gap-2 pb-2">
          <Monitor className="w-3.5 h-3.5 text-muted-foreground" />
          <p className="text-[11px] text-muted-foreground">
            Uses browser Speech Recognition + Vamsee AI backend TTS
          </p>
        </div>
      </div>
    </div>
  );
};

export default VoiceAssistant;
