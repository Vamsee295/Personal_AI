"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import {
  Mic, MicOff, Volume2, StopCircle, AlertCircle,
  Zap, Terminal, CheckCircle2, Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { executeCommand } from "@/lib/agentApi";

// ── Types ──────────────────────────────────────────────────────────────────────

type Phase = "idle" | "recording" | "transcribing" | "executing" | "speaking" | "error";

interface LogEntry {
  id: number;
  phase: "command" | "action" | "result" | "error";
  text: string;
  time: string;
  action?: string;
}

// ── Config ─────────────────────────────────────────────────────────────────────

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const QUICK_COMMANDS = [
  { label: "Open VS Code",        cmd: "open vs code"         },
  { label: "Take Screenshot",     cmd: "take a screenshot"     },
  { label: "Open YouTube",        cmd: "open youtube"          },
  { label: "Open Calculator",     cmd: "open calculator"       },
  { label: "Show Desktop",        cmd: "show the desktop"      },
  { label: "What time is it?",    cmd: "check the time"        },
];

const PHASE_LABEL: Record<Phase, string> = {
  idle:         "Hold mic or say a quick command",
  recording:    "Listening… speak now",
  transcribing: "Transcribing your voice…",
  executing:    "Executing command…",
  speaking:     "AI is responding…",
  error:        "Something went wrong",
};

const PHASE_COLOR: Record<Phase, string> = {
  idle:         "text-muted-foreground",
  recording:    "text-blue-400",
  transcribing: "text-yellow-400",
  executing:    "text-purple-400",
  speaking:     "text-emerald-400",
  error:        "text-red-400",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

let _logId = 0;
const makeLog = (phase: LogEntry["phase"], text: string, action?: string): LogEntry => ({
  id: ++_logId,
  phase,
  text,
  action,
  time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
});

function browserSpeak(text: string, onEnd?: () => void) {
  if (!("speechSynthesis" in window)) { onEnd?.(); return; }
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text);
  utt.rate = 1.0;
  utt.pitch = 1.0;
  utt.volume = 1.0;
  utt.onend = () => onEnd?.();
  utt.onerror = () => onEnd?.();
  window.speechSynthesis.speak(utt);
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function VoiceAssistant() {
  const [phase, setPhase]           = useState<Phase>("idle");
  const [log, setLog]               = useState<LogEntry[]>([]);
  const [errorMsg, setErrorMsg]     = useState("");
  const [lastCommand, setLastCmd]   = useState("");
  const [lastResponse, setLastResp] = useState("");
  const [barHeights, setBarHeights] = useState<number[]>(Array(28).fill(4));

  const mediaRef    = useRef<MediaRecorder | null>(null);
  const chunksRef   = useRef<Blob[]>([]);
  const animFrameRef = useRef<number>(0);
  const logEndRef   = useRef<HTMLDivElement>(null);

  // ── Waveform animation ──────────────────────────────────────────────────────
  useEffect(() => {
    if (phase === "recording") {
      const animate = () => {
        setBarHeights(prev => prev.map(() => 4 + Math.random() * 44));
        animFrameRef.current = requestAnimationFrame(animate);
      };
      animFrameRef.current = requestAnimationFrame(animate);
    } else {
      cancelAnimationFrame(animFrameRef.current);
      setBarHeights(Array(28).fill(phase === "idle" || phase === "error" ? 4 : 20));
    }
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [phase]);

  // ── Auto-scroll log ─────────────────────────────────────────────────────────
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [log]);

  const appendLog = (entry: LogEntry) => setLog(prev => [entry, ...prev].slice(0, 50));

  // ── Core pipeline: text command → /api/voice/execute → speak ─────────────────
  const runCommand = useCallback(async (text: string) => {
    setLastCmd(text);
    appendLog(makeLog("command", text));
    setPhase("executing");

    try {
      const res = await fetch(`${BACKEND}/api/voice/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: text }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Executor failed");
      }

      const action  = (data.action?.action as string) || "";
      const spoken  = (data.spoken_response as string) || "Done.";
      const success = data.success as boolean;

      appendLog(makeLog(
        success ? "action" : "error",
        `${action ? `[${action}] ` : ""}${data.result?.message || data.result?.error || spoken}`,
        action,
      ));

      setLastResp(spoken);
      setPhase("speaking");
      browserSpeak(spoken, () => setPhase("idle"));

    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setErrorMsg(msg);
      appendLog(makeLog("error", msg));
      setPhase("error");
      setTimeout(() => setPhase("idle"), 4000);
    }
  }, []);

  // ── Record from browser mic → send to /api/voice/stt ───────────────────────
  const startRecording = useCallback(async () => {
    setErrorMsg("");
    setPhase("recording");

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setErrorMsg("Microphone permission denied. Allow mic access in your browser and try again.");
      setPhase("error");
      setTimeout(() => setPhase("idle"), 5000);
      return;
    }

    const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
    chunksRef.current = [];
    recorder.ondataavailable = e => e.data.size > 0 && chunksRef.current.push(e.data);

    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());

      // Wait a moment for final chunk to flush
      await new Promise(r => setTimeout(r, 100));

      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      setPhase("transcribing");

      try {
        const form = new FormData();
        form.append("audio", blob, "voice.webm");

        const sttRes = await fetch(`${BACKEND}/api/voice/stt`, {
          method: "POST",
          body: form,
        });

        if (!sttRes.ok) {
          const errData = await sttRes.json().catch(() => ({ detail: "STT failed" }));
          throw new Error(errData.detail || "STT failed");
        }

        const { text, success, message } = await sttRes.json();

        if (!success || !text) {
          setPhase("idle");
          appendLog(makeLog("error", message || "No speech detected — speak clearly and try again."));
          setErrorMsg(message || "No speech detected. Speak clearly.");
          setTimeout(() => setErrorMsg(""), 4000);
          return;
        }

        await runCommand(text);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "STT error";
        setErrorMsg(msg);
        appendLog(makeLog("error", msg));
        setPhase("error");
        setTimeout(() => setPhase("idle"), 4000);
      }
    };

    mediaRef.current = recorder;
    recorder.start(100); // collect chunks every 100ms

    // AUTO-STOP after 10 seconds (fail-safe)
    const autoStop = setTimeout(() => {
      if (mediaRef.current?.state === "recording") {
        mediaRef.current.stop();
      }
    }, 10000);
  }, [runCommand]);

  const stopRecording = useCallback(() => {
    mediaRef.current?.stop();
  }, []);

  const handlePointerDown = (e: React.PointerEvent) => {
    e.preventDefault();
    if (phase === "speaking") stopSpeaking();
    else if (phase === "idle") startRecording();
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    e.preventDefault();
    if (phase === "recording") stopRecording();
  };

  const handleQuickCommand = (cmd: string) => {
    if (phase !== "idle") return;
    runCommand(cmd);
  };

  const stopSpeaking = () => {
    window.speechSynthesis?.cancel();
    setPhase("idle");
  };

  // ── Render ──────────────────────────────────────────────────────────────────
  const isActive = phase !== "idle" && phase !== "error";

  return (
    <div className="h-full flex flex-col bg-background overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold text-foreground flex items-center gap-2">
              <Zap className="w-4 h-4 text-primary" />
              Voice Assistant
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Speak to Ultron · Browser mic → Faster-Whisper → Ollama executor
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className={cn(
              "w-2 h-2 rounded-full",
              phase === "idle" ? "bg-emerald-500" : "bg-primary animate-pulse"
            )} />
            <span className="text-xs text-muted-foreground capitalize">{phase}</span>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col items-center justify-center gap-6 px-6 py-6 overflow-auto">

        {/* Status label */}
        <p className={cn(
          "text-sm font-medium tracking-wide transition-colors duration-300",
          PHASE_COLOR[phase]
        )}>
          {PHASE_LABEL[phase]}
        </p>

        {/* Waveform visualiser */}
        <div className="flex items-center gap-[3px] h-16">
          {barHeights.map((h, i) => (
            <div
              key={i}
              className={cn(
                "w-[3px] rounded-full transition-all",
                phase === "recording"   ? "bg-blue-400"    :
                phase === "executing"   ? "bg-purple-400"  :
                phase === "speaking"    ? "bg-emerald-400" :
                phase === "transcribing"? "bg-yellow-400"  :
                "bg-border"
              )}
              style={{
                height: `${h}px`,
                transitionDuration: phase === "recording" ? "80ms" : "300ms",
              }}
            />
          ))}
        </div>

        {/* Mic / status button */}
        <div className="relative flex items-center justify-center">
          {phase === "recording" && (
            <div className="absolute w-24 h-24 rounded-full border-2 border-blue-400/40 animate-ping" />
          )}
          <button
            onPointerDown={handlePointerDown}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
            onContextMenu={(e) => e.preventDefault()} // prevent long press menu on mobile
            disabled={phase === "transcribing" || phase === "executing"}
            className={cn(
              "relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-200 shadow-lg",
              phase === "idle"         && "bg-card border-2 border-border hover:border-primary/60 hover:scale-105",
              phase === "recording"    && "bg-blue-500/20 border-2 border-blue-400 scale-110",
              phase === "transcribing" && "bg-yellow-500/20 border-2 border-yellow-400 cursor-not-allowed",
              phase === "executing"    && "bg-purple-500/20 border-2 border-purple-400 cursor-not-allowed",
              phase === "speaking"     && "bg-emerald-500/20 border-2 border-emerald-400 hover:scale-105",
              phase === "error"        && "bg-red-500/20 border-2 border-red-400",
            )}
          >
            {phase === "idle"         && <Mic       className="w-7 h-7 text-muted-foreground" />}
            {phase === "recording"    && <StopCircle className="w-7 h-7 text-blue-400" />}
            {phase === "transcribing" && <Loader2    className="w-7 h-7 text-yellow-400 animate-spin" />}
            {phase === "executing"    && <Loader2    className="w-7 h-7 text-purple-400 animate-spin" />}
            {phase === "speaking"     && <Volume2    className="w-7 h-7 text-emerald-400" />}
            {phase === "error"        && <MicOff     className="w-7 h-7 text-red-400" />}
          </button>
        </div>

        {/* Info card */}
        <div className="w-full max-w-lg bg-card border border-border rounded-xl px-5 py-4 min-h-[64px] space-y-2">
          {phase === "error" && (
            <div className="flex items-start gap-2 text-red-400 text-[12px]">
              <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              {errorMsg || "Unknown error"}
            </div>
          )}
          {lastCommand && (
            <p className="text-[12px] text-muted-foreground">
              You: <span className="text-foreground font-medium">"{lastCommand}"</span>
            </p>
          )}
          {lastResponse && (phase === "speaking" || phase === "idle") && (
            <p className="text-[13px] text-foreground leading-relaxed">{lastResponse}</p>
          )}
          {!lastCommand && phase === "idle" && (
            <p className="text-[13px] text-muted-foreground">
              Press and <strong className="text-foreground">hold</strong> the microphone button to speak, then release.
            </p>
          )}
          {phase === "recording" && (
            <p className="text-[12px] text-blue-400 animate-pulse">
              🎙 Recording… keep holding. Release when finished.
            </p>
          )}
        </div>

        {/* Quick commands */}
        <div className="flex flex-wrap gap-2 justify-center max-w-lg">
          {QUICK_COMMANDS.map(({ label, cmd }) => (
            <button
              key={cmd}
              onClick={() => handleQuickCommand(cmd)}
              disabled={phase !== "idle"}
              className={cn(
                "px-4 py-2 rounded-full border text-[13px] font-medium transition-all duration-150",
                "bg-card border-border text-foreground",
                "hover:border-primary/60 hover:bg-primary/10 hover:scale-[1.02]",
                "disabled:opacity-40 disabled:cursor-not-allowed disabled:scale-100",
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Conversation log */}
        {log.length > 0 && (
          <div className="w-full max-w-lg">
            <p className="text-[11px] text-muted-foreground mb-2 flex items-center gap-1.5">
              <Terminal className="w-3 h-3" /> Conversation log
            </p>
            <div className="bg-card border border-border rounded-xl overflow-hidden max-h-48 overflow-y-auto">
              {[...log].reverse().map(entry => (
                <div
                  key={entry.id}
                  className={cn(
                    "px-4 py-2 text-[12px] border-b border-border/40 last:border-b-0 font-mono flex items-start gap-2",
                    entry.phase === "command" ? "text-blue-400"    :
                    entry.phase === "action"  ? "text-purple-400"  :
                    entry.phase === "result"  ? "text-emerald-400" :
                    "text-red-400"
                  )}
                >
                  <span className="text-[10px] text-muted-foreground/50 shrink-0 mt-0.5">{entry.time}</span>
                  <span>
                    {entry.phase === "command" && <> <span className="opacity-60">You:</span> {entry.text}</>}
                    {entry.phase === "action"  && <> <CheckCircle2 className="inline w-3 h-3 mr-1" />{entry.text}</>}
                    {entry.phase === "error"   && <> <AlertCircle  className="inline w-3 h-3 mr-1" />{entry.text}</>}
                  </span>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        )}

        {/* Footer note */}
        <p className="text-[11px] text-muted-foreground/50 pb-2 text-center">
          Browser mic → Faster-Whisper STT → Ollama Executor → Browser TTS
        </p>
      </div>
    </div>
  );
}


// ── Spoken response builder ────────────────────────────────────────────────────

function buildSpokenResponse(action: string, parsed: Record<string, unknown>, fallback: string): string {
  const t = (key: string) => (parsed[key] as string) || "";
  switch (action) {
    case "open_app":              return `Opening ${t("target")}.`;
    case "open_url":              return `Opening ${t("target")} in your browser.`;
    case "search_youtube":        return `Searching YouTube for ${t("query")}.`;
    case "type_text":             return `Text typed.`;
    case "press_key":             return `Pressed ${t("value")}.`;
    case "take_screenshot":       return `Screenshot saved.`;
    case "scroll":                return `Scrolled ${t("value")}.`;
    case "send_whatsapp_message": return `Sending message to ${t("target")} on WhatsApp.`;
    case "read_whatsapp":         return `Reading messages from ${t("target")}.`;
    default:                      return fallback;
  }
}
