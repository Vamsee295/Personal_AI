import React, { useState, useCallback, useEffect, useRef } from "react";
import Head from "next/head";
import {
  Terminal, Zap, Eye, Send, MessageSquare, Camera,
  Wifi, WifiOff, Cpu, RefreshCw, ChevronRight,
  ToggleLeft, ToggleRight, Layers, Database, ChevronDown,
  CheckCircle, XCircle, Clock, Mic, MicOff, Volume2, Settings2,
} from "lucide-react";
import AgentLog, { LogEntry, LogType } from "@/components/AgentLog";
import ScreenshotPreview from "@/components/ScreenshotPreview";
import {
  executeCommand,
  runVisionLoop,
  sendWhatsApp,
  getHealth,
  checkOllama,
  executeDirectAction,
  getMemoryRecent,
  getMemoryStats,
  getPreferences,
  clearOldMemories,
  MemoryCommand,
  MemoryStats,
} from "@/lib/agentApi";

// ── Types ─────────────────────────────────────────────────────────────────────
interface BackendStatus {
  fastapi: "online" | "offline" | "checking";
  ollama: "online" | "offline" | "checking";
  model: string;
}

// ── Quick action presets ──────────────────────────────────────────────────────
const QUICK_ACTIONS = [
  { label: "Screenshot",   icon: Camera,  command: null,         action: { action: "take_screenshot", target: "", value: "", x: 0, y: 0 } },
  { label: "Notepad",      icon: Terminal, command: "Open Notepad", action: null },
  { label: "Chrome",       icon: Zap,      command: "Open Chrome",  action: null },
  { label: "Lock screen",  icon: Layers,   command: null,           action: { action: "press_key", target: "", value: "win+l", x: 0, y: 0 } },
];

// ── Log factory ───────────────────────────────────────────────────────────────
let _logId = 0;
function makeLog(type: LogType, message: string): LogEntry {
  return { id: String(++_logId), timestamp: new Date(), type, message };
}

// ── Status dot ───────────────────────────────────────────────────────────────
function StatusDot({ state }: { state: "online" | "offline" | "checking" }) {
  if (state === "checking") return <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />;
  if (state === "online")   return <span className="w-2 h-2 rounded-full bg-emerald-500 animate-status-pulse" />;
  return <span className="w-2 h-2 rounded-full bg-red-500" />;
}

// =============================================================================
//  MAIN PAGE
// =============================================================================

export default function ControlPage() {
  // ── State ───────────────────────────────────────────────────────────────────
  const [logs, setLogs]                   = useState<LogEntry[]>([makeLog("system", "Agent Control Center initialised. Ready.")]);
  const [isRunning, setIsRunning]         = useState(false);
  const [command, setCommand]             = useState("");
  const [visionMode, setVisionMode]       = useState(false);
  const [maxSteps, setMaxSteps]           = useState(5);
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [lastAction, setLastAction]       = useState<Record<string, unknown> | null>(null);
  const [backend, setBackend]             = useState<BackendStatus>({
    fastapi: "checking", ollama: "checking", model: "—",
  });

  // WhatsApp inputs
  const [waContact, setWaContact] = useState("");
  const [waMessage, setWaMessage] = useState("");

  // Memory state
  const [memoryOpen,    setMemoryOpen]    = useState(true);
  const [memCommands,   setMemCommands]   = useState<MemoryCommand[]>([]);
  const [memStats,      setMemStats]      = useState<MemoryStats | null>(null);
  const [memPrefs,      setMemPrefs]      = useState<Record<string, string>>({});
  const [memClearing,   setMemClearing]   = useState(false);

  // Voice state
  const [isListening,   setIsListening]   = useState(false);
  const [wakeMode,      setWakeMode]      = useState(false);
  const [voiceSettings, setVoiceSettings] = useState(false);
  const [ttsRate,       setTtsRate]       = useState(175);
  const [ttsGender,     setTtsGender]     = useState("male");
  const wsRef = useRef<WebSocket | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  // ── Helpers ─────────────────────────────────────────────────────────────────
  const addLog = useCallback((type: LogType, message: string) => {
    setLogs(prev => [...prev, makeLog(type, message)]);
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([makeLog("system", "Log cleared.")]);
  }, []);

  // ── Memory fetch ────────────────────────────────────────────────────────────
  const fetchMemory = useCallback(async () => {
    const [recentRes, statsRes, prefsRes] = await Promise.all([
      getMemoryRecent(5),
      getMemoryStats(),
      getPreferences(),
    ]);
    if (recentRes.success && recentRes.data) setMemCommands(recentRes.data.commands);
    if (statsRes.success && statsRes.data)   setMemStats(statsRes.data);
    if (prefsRes.success && prefsRes.data)   setMemPrefs(prefsRes.data.preferences);
  }, []);

  // ── Backend health check ────────────────────────────────────────────────────
  const checkStatus = useCallback(async () => {
    setBackend(prev => ({ ...prev, fastapi: "checking", ollama: "checking" }));

    const [healthResult, ollamaOk] = await Promise.all([
      getHealth(),
      checkOllama(),
    ]);

    setBackend({
      fastapi: healthResult.success ? "online" : "offline",
      ollama: ollamaOk ? "online" : "offline",
      model: healthResult.data?.model || "qwen2.5-coder:7b",
    });
  }, []);

  useEffect(() => {
    checkStatus();
    fetchMemory();
    const interval = setInterval(checkStatus, 30_000);
    return () => {
      clearInterval(interval);
      // Clean up voice WebSocket on unmount
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [checkStatus, fetchMemory]);

  // ── Voice mic handler ───────────────────────────────────────────────────────
  const handleMicClick = useCallback(() => {
    if (isListening) {
      // Stop
      if (wsRef.current) {
        wsRef.current.send(JSON.stringify({ action: "stop" }));
        wsRef.current.close();
        wsRef.current = null;
      }
      setIsListening(false);
      addLog("info", "Voice listening stopped.");
      return;
    }

    // Start
    setIsListening(true);
    addLog("action", "Mic activated — speak your command (6s)...");

    const ws = new WebSocket("ws://localhost:8000/voice/ws");
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ action: "start_listening", duration: 6 }));
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.status === "listening") {
          addLog("info", "Recording... speak now.");
        } else if (msg.status === "done") {
          const text = msg.transcribed || "";
          if (text) {
            addLog("info", `Transcribed: "${text}"`);
            setCommand(text);
          }
          if (msg.action_taken) setLastAction(msg.action_taken);
          const resultMsg = msg.spoken || (msg.result?.message) || (msg.success ? "Done" : "Failed");
          addLog(msg.success ? "success" : "error", resultMsg);
          fetchMemory();
          setIsListening(false);
          wsRef.current = null;
        } else if (msg.status === "error") {
          addLog("error", msg.message || "Voice error");
          setIsListening(false);
          wsRef.current = null;
        }
      } catch {
        // non-JSON message
      }
    };

    ws.onerror = () => {
      addLog("error", "Voice WebSocket error. Is the backend running?");
      setIsListening(false);
      wsRef.current = null;
    };

    ws.onclose = () => {
      setIsListening(false);
      wsRef.current = null;
    };
  }, [isListening, addLog, fetchMemory]);

  // ── Wake mode toggle ────────────────────────────────────────────────────────
  const handleWakeMode = useCallback(async () => {
    if (wakeMode) {
      // Disable -- just kill the WS
      if (wsRef.current) {
        wsRef.current.send(JSON.stringify({ action: "stop" }));
        wsRef.current.close();
        wsRef.current = null;
      }
      setWakeMode(false);
      addLog("info", "Wake mode disabled.");
      return;
    }

    setWakeMode(true);
    addLog("action", "Wake mode ON — say \"Hey Ultron\" to activate");

    const ws = new WebSocket("ws://localhost:8000/voice/ws");
    wsRef.current = ws;

    ws.onopen = () => ws.send(JSON.stringify({ action: "start_wake_mode" }));

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.status === "wake_mode_on") addLog("success", "Wake word listener active.");
        if (msg.status === "done") {
          const text = msg.transcribed || "";
          if (text) { addLog("info", `Voice: "${text}"`); setCommand(text); }
          if (msg.action_taken) setLastAction(msg.action_taken);
          addLog(msg.success ? "success" : "error", msg.spoken || "Command processed.");
          fetchMemory();
        }
      } catch { /**/ }
    };

    ws.onerror = () => { setWakeMode(false); addLog("error", "Wake mode WS error"); wsRef.current = null; };
    ws.onclose = () => { setWakeMode(false); wsRef.current = null; };
  }, [wakeMode, addLog, fetchMemory]);

  // ── Speak log entry via TTS ────────────────────────────────────────────────────
  const speakText = useCallback(async (text: string) => {
    try {
      await fetch("http://localhost:8000/voice/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
    } catch { /**/ }
  }, []);

  // ── Execute a command ───────────────────────────────────────────────────────
  const runCommand = useCallback(async (cmd: string) => {
    if (!cmd.trim() || isRunning) return;
    setIsRunning(true);
    addLog("action", `> ${cmd}`);

    try {
      if (visionMode) {
        addLog("info", `Starting vision loop (max ${maxSteps} steps)...`);
        const result = await runVisionLoop(cmd, maxSteps);
        if (result.success && result.data) {
          const { total_steps, step_log } = result.data;
          addLog("info", `Loop ran ${total_steps} step(s).`);
          step_log.forEach(step => {
            const actionName = (step.action as Record<string, unknown>)?.action as string ?? "?";
            const ok = (step.result as Record<string, unknown>)?.success;
            addLog(ok ? "success" : "error", `Step ${step.step}: ${actionName} — ${ok ? "OK" : "Failed"}`);
            if (step.action) setLastAction(step.action as Record<string, unknown>);
          });
          addLog("success", "Vision loop complete.");
        } else {
          addLog("error", result.error || "Vision loop failed.");
        }
      } else {
        addLog("info", "Sending to Ollama for action planning...");
        const result = await executeCommand(cmd);
        if (result.success && result.data) {
          const { parsed_action, result: execResult } = result.data;
          addLog("action", `Action: ${JSON.stringify(parsed_action)}`);
          setLastAction(parsed_action);
          if (execResult?.success) {
            addLog("success", execResult.message || "Action executed successfully.");
          } else {
            addLog("error", execResult?.error || "Execution failed.");
          }
        } else {
          addLog("error", result.error || "Command failed.");
        }
      }
    } finally {
      setIsRunning(false);
      // Refresh memory after every command
      fetchMemory();
    }
  }, [isRunning, visionMode, maxSteps, addLog, fetchMemory]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!command.trim()) return;
    runCommand(command);
    setCommand("");
  };

  // ── Quick actions ───────────────────────────────────────────────────────────
  const handleQuickAction = useCallback(async (qa: typeof QUICK_ACTIONS[number]) => {
    if (isRunning) return;

    if (qa.command) {
      setCommand(qa.command);
      await runCommand(qa.command);
      return;
    }

    if (qa.action) {
      setIsRunning(true);
      addLog("action", `Quick action: ${qa.label}`);
      try {
        const res = await executeDirectAction(qa.action);
        if (res.success) {
          addLog("success", `${qa.label} — done.`);
          if (qa.action.action === "take_screenshot") {
            // After screenshot, refresh preview
            setTimeout(() => setScreenshotUrl(`/api/screenshot/latest?ts=${Date.now()}`), 800);
          }
        } else {
          addLog("error", res.error || "Quick action failed.");
        }
      } finally {
        setIsRunning(false);
      }
    }
  }, [isRunning, addLog, runCommand]);

  // ── WhatsApp send ───────────────────────────────────────────────────────────
  const handleSendWhatsApp = useCallback(async () => {
    if (!waContact.trim() || !waMessage.trim() || isRunning) return;
    setIsRunning(true);
    addLog("action", `WhatsApp → ${waContact}: "${waMessage.slice(0, 40)}..."`);
    try {
      const result = await sendWhatsApp(waContact, waMessage);
      if (result.success) {
        addLog("success", `Message sent to ${result.data?.chat_opened || waContact}.`);
        setWaMessage("");
      } else {
        addLog("error", result.error || "WhatsApp send failed.");
      }
    } finally {
      setIsRunning(false);
    }
  }, [waContact, waMessage, isRunning, addLog]);

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <>
      <Head>
        <title>Agent Control — Ultron</title>
        <meta name="description" content="Control panel for Ultron — execute actions, run vision loops, send WhatsApp messages" />
      </Head>

      <div className="h-full flex flex-col overflow-hidden">
        {/* ── Page header ───────────────────────────────────────────────── */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div
              className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center shrink-0"
              style={{ boxShadow: "0 0 18px rgba(124,80,255,0.4)" }}
            >
              <Terminal className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-foreground leading-none">Agent Control Center</h1>
              <p className="text-[11px] text-muted-foreground mt-0.5 flex items-center gap-1.5">
                <StatusDot state={backend.fastapi} />
                {backend.fastapi === "online" ? "Backend online" : backend.fastapi === "checking" ? "Checking..." : "Backend offline"}
              </p>
            </div>
          </div>
          <button
            onClick={checkStatus}
            className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/60 transition-all"
            title="Refresh status"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* ── Two-column layout ─────────────────────────────────────────── */}
        <div className="flex-1 overflow-auto">
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-0 h-full min-h-0">

            {/* ═══ LEFT COLUMN ═══════════════════════════════════════════ */}
            <div className="flex flex-col gap-5 px-6 py-5 border-r border-border overflow-y-auto">

              {/* ── Command input ──────────────────────────────────────── */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                    Natural Language Command
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-muted-foreground">Vision mode</span>
                    <button
                      onClick={() => setVisionMode(v => !v)}
                      className={`transition-colors ${visionMode ? "text-violet-400" : "text-slate-600"}`}
                      title={visionMode ? "Vision ON: sees screen before acting" : "Vision OFF: direct command execution"}
                    >
                      {visionMode
                        ? <ToggleRight className="w-5 h-5" />
                        : <ToggleLeft className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                <form onSubmit={handleSubmit} className="flex gap-2">
                  <div className="relative flex-1">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none">
                      <ChevronRight className="w-3.5 h-3.5" />
                    </span>
                    <input
                      ref={inputRef}
                      id="agent-command-input"
                      type="text"
                      value={command}
                      onChange={e => setCommand(e.target.value)}
                      disabled={isRunning}
                      placeholder={visionMode ? "Describe goal (agent will see + act)..." : "Tell the agent what to do..."}
                      className="w-full bg-[#0d0d12] border border-white/[0.08] rounded-xl pl-8 pr-4 py-3 text-[13px] text-foreground placeholder:text-slate-600 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all disabled:opacity-50 font-mono"
                    />
                  </div>

                  {/* 🎤 Mic button */}
                  <button
                    type="button"
                    id="voice-mic-button"
                    onClick={handleMicClick}
                    disabled={isRunning}
                    title={isListening ? "Stop listening" : "Click to speak a command"}
                    className={`relative p-3 rounded-xl border transition-all flex items-center justify-center disabled:opacity-40 ${
                      isListening
                        ? "bg-red-500/20 border-red-500/50 text-red-400"
                        : "bg-[#0d0d12] border-white/[0.08] text-slate-400 hover:border-violet-500/40 hover:text-violet-400"
                    }`}
                    style={isListening ? { boxShadow: "0 0 16px rgba(239,68,68,0.35)" } : {}}
                  >
                    {isListening
                      ? <MicOff className="w-4 h-4" />
                      : <Mic className="w-4 h-4" />}
                    {/* Pulsing ring when listening */}
                    {isListening && (
                      <span className="absolute inset-0 rounded-xl border border-red-500 animate-ping opacity-40" />
                    )}
                  </button>

                  <button
                    type="submit"
                    disabled={isRunning || !command.trim()}
                    id="agent-run-button"
                    className="px-5 py-3 rounded-xl bg-violet-600 text-white text-[13px] font-medium hover:bg-violet-500 active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
                    style={{ boxShadow: "0 0 20px rgba(124,80,255,0.3)" }}
                  >
                    {isRunning ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Zap className="w-4 h-4" />
                    )}
                    {isRunning ? "Running" : "Run"}
                  </button>
                </form>

                {/* Vision mode + Wake mode bar */}
                <div className="flex items-center gap-3">
                  {visionMode && (
                    <div className="flex items-center gap-3 flex-1 px-4 py-2.5 rounded-xl bg-violet-500/10 border border-violet-500/20">
                      <Eye className="w-3.5 h-3.5 text-violet-400 shrink-0" />
                      <span className="text-[12px] text-violet-300">Agent will capture screen → OCR → decide action</span>
                      <div className="ml-auto flex items-center gap-2">
                        <span className="text-[11px] text-violet-400">Max steps:</span>
                        <input type="number" min={1} max={20} value={maxSteps}
                          onChange={e => setMaxSteps(Number(e.target.value))}
                          className="w-14 bg-violet-500/10 border border-violet-500/30 rounded-lg px-2 py-1 text-[12px] text-violet-200 text-center focus:outline-none focus:border-violet-400" />
                      </div>
                    </div>
                  )}

                  {/* Wake mode pill */}
                  <button
                    id="wake-mode-toggle"
                    onClick={handleWakeMode}
                    className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-[11px] font-medium transition-all ${
                      wakeMode
                        ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"
                        : "border-white/[0.06] text-slate-500 hover:text-slate-300 hover:border-white/10"
                    }`}
                  >
                    {wakeMode && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}
                    <Mic className="w-3 h-3" />
                    {wakeMode ? "Always listening" : "Wake word"}
                  </button>

                  {/* Voice settings toggle */}
                  <button
                    onClick={() => setVoiceSettings(v => !v)}
                    className="p-2 rounded-lg border border-white/[0.06] text-slate-500 hover:text-slate-300 transition-all"
                    title="Voice settings"
                  >
                    <Settings2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* ── Voice settings panel (collapsible) ────────────────── */}
              {voiceSettings && (
                <div className="rounded-xl bg-[#0d0d12] border border-white/[0.06] p-4 space-y-3 animate-fade-slide-up">
                  <div className="flex items-center gap-2 mb-1">
                    <Volume2 className="w-3.5 h-3.5 text-violet-400" />
                    <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Voice Settings</span>
                  </div>

                  {/* Speed slider */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-[11px] text-muted-foreground">Speech speed</label>
                      <span className="text-[11px] text-violet-300">{ttsRate} WPM</span>
                    </div>
                    <input
                      type="range"
                      min={100} max={280} step={10}
                      value={ttsRate}
                      onChange={e => setTtsRate(Number(e.target.value))}
                      className="w-full accent-violet-500 h-1.5 rounded-full"
                    />
                    <div className="flex justify-between text-[10px] text-slate-600">
                      <span>Slow</span><span>Normal</span><span>Fast</span>
                    </div>
                  </div>

                  {/* Gender select */}
                  <div className="flex items-center gap-3">
                    <label className="text-[11px] text-muted-foreground w-16 shrink-0">Voice</label>
                    <div className="flex gap-2">
                      {["male", "female"].map(g => (
                        <button
                          key={g}
                          onClick={() => setTtsGender(g)}
                          className={`px-3 py-1 rounded-lg text-[11px] border transition-all capitalize ${
                            ttsGender === g
                              ? "bg-violet-600/20 border-violet-500/40 text-violet-300"
                              : "border-white/[0.06] text-slate-500 hover:border-white/10"
                          }`}
                        >
                          {g}
                        </button>
                      ))}
                    </div>

                    <button
                      onClick={async () => {
                        await fetch("http://localhost:8000/voice/settings", {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ rate: ttsRate, gender: ttsGender }),
                        });
                        addLog("success", `Voice: ${ttsRate}WPM, ${ttsGender}`);
                      }}
                      className="ml-auto px-3 py-1.5 rounded-lg bg-violet-600/20 border border-violet-500/30 text-violet-300 text-[11px] hover:bg-violet-600/30 transition-all"
                    >
                      Apply
                    </button>
                  </div>

                  {/* Test TTS */}
                  <button
                    onClick={() => speakText("Hello, I am Ultron. This is how I sound.")}
                    className="w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-white/[0.04] text-[11px] text-muted-foreground hover:text-foreground transition-all"
                  >
                    <Volume2 className="w-3 h-3" />
                    Test voice
                  </button>
                </div>
              )}

              {/* ── Quick actions ──────────────────────────────────────── */}
              <div className="space-y-2">
                <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Quick Actions
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {QUICK_ACTIONS.map((qa) => (
                    <button
                      key={qa.label}
                      id={`quick-${qa.label.toLowerCase().replace(/\s+/g, "-")}`}
                      onClick={() => handleQuickAction(qa)}
                      disabled={isRunning}
                      className="flex flex-col items-center gap-2 px-3 py-3.5 rounded-xl bg-[#0d0d12] border border-white/[0.06] hover:border-violet-500/40 hover:bg-violet-500/5 transition-all group disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
                    >
                      <qa.icon className="w-4 h-4 text-muted-foreground group-hover:text-violet-400 transition-colors" />
                      <span className="text-[11px] font-medium text-muted-foreground group-hover:text-foreground transition-colors">
                        {qa.label}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* ── WhatsApp section ───────────────────────────────────── */}
              <div className="space-y-2">
                <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <MessageSquare className="w-3 h-3" />
                  WhatsApp
                </label>
                <div className="p-4 rounded-xl bg-[#0d0d12] border border-white/[0.06] space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-muted-foreground mb-1 block">Contact name</label>
                      <input
                        id="wa-contact-input"
                        type="text"
                        value={waContact}
                        onChange={e => setWaContact(e.target.value)}
                        placeholder="e.g. Ravi"
                        disabled={isRunning}
                        className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 text-[12px] text-foreground placeholder:text-slate-600 focus:outline-none focus:border-violet-500/40 transition-all disabled:opacity-50"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-muted-foreground mb-1 block">Message</label>
                      <input
                        id="wa-message-input"
                        type="text"
                        value={waMessage}
                        onChange={e => setWaMessage(e.target.value)}
                        placeholder="e.g. Good morning!"
                        disabled={isRunning}
                        onKeyDown={e => e.key === "Enter" && handleSendWhatsApp()}
                        className="w-full bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 text-[12px] text-foreground placeholder:text-slate-600 focus:outline-none focus:border-violet-500/40 transition-all disabled:opacity-50"
                      />
                    </div>
                  </div>
                  <button
                    id="wa-send-button"
                    onClick={handleSendWhatsApp}
                    disabled={isRunning || !waContact.trim() || !waMessage.trim()}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-emerald-600/20 border border-emerald-500/30 text-emerald-300 text-[12px] font-medium hover:bg-emerald-600/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]"
                  >
                    <Send className="w-3.5 h-3.5" />
                    {isRunning ? "Sending..." : "Send on WhatsApp"}
                  </button>
                </div>
              </div>

              {/* ── Memory Panel ───────────────────────────────────────── */}
              <div className="space-y-2">
                <button
                  onClick={() => setMemoryOpen(v => !v)}
                  className="flex items-center gap-2 w-full text-left group"
                >
                  <Database className="w-3 h-3 text-amber-400" />
                  <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider cursor-pointer group-hover:text-foreground transition-colors">
                    Memory
                  </label>
                  {memStats && (
                    <span className="text-[10px] text-amber-400/70 ml-1">
                      {memStats.total_commands} cmd{memStats.total_commands !== 1 ? "s" : ""} · {Math.round(memStats.success_rate * 100)}% success
                    </span>
                  )}
                  <ChevronDown className={`w-3 h-3 text-muted-foreground ml-auto transition-transform ${memoryOpen ? "rotate-180" : ""}`} />
                </button>

                {memoryOpen && (
                  <div className="rounded-xl bg-[#0d0d12] border border-white/[0.06] overflow-hidden animate-fade-slide-up">

                    {/* Stats bar */}
                    {memStats && (
                      <div className="flex items-center gap-4 px-4 py-2.5 border-b border-white/[0.04] bg-amber-500/5">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3 h-3 text-amber-400" />
                          <span className="text-[11px] text-amber-300">{memStats.total_commands} total</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <CheckCircle className="w-3 h-3 text-emerald-400" />
                          <span className="text-[11px] text-emerald-300">{Math.round(memStats.success_rate * 100)}%</span>
                        </div>
                        <div className="text-[11px] text-slate-500">
                          top: <span className="text-slate-300">{memStats.most_used_action}</span>
                        </div>
                        <div className="text-[11px] text-slate-500 ml-auto">
                          {memStats.db_size_kb} KB
                        </div>
                      </div>
                    )}

                    {/* Recent commands list */}
                    <div className="divide-y divide-white/[0.03]">
                      {memCommands.length === 0 ? (
                        <div className="px-4 py-5 text-center text-[12px] text-slate-600">
                          No commands remembered yet.
                          <br />
                          <span className="text-[11px]">Run a command above to start building memory.</span>
                        </div>
                      ) : (
                        memCommands.slice(0, 5).map(cmd => (
                          <div key={cmd.id} className="flex items-start gap-3 px-4 py-2.5 hover:bg-white/[0.02] transition-colors">
                            {cmd.success
                              ? <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0 mt-0.5" />
                              : <XCircle className="w-3 h-3 text-red-500 shrink-0 mt-0.5" />}
                            <div className="flex-1 min-w-0">
                              <p className="text-[12px] text-foreground truncate">{cmd.user_input}</p>
                              <p className="text-[10px] text-slate-500">
                                {typeof cmd.action_taken === "object" && cmd.action_taken !== null
                                  ? (cmd.action_taken as Record<string, unknown>).action as string ?? "?"
                                  : "?"}
                                {" · "}{cmd.relative_time}
                              </p>
                            </div>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Preferences */}
                    {Object.keys(memPrefs).length > 0 && (
                      <div className="border-t border-white/[0.04] px-4 py-2.5 bg-white/[0.01]">
                        <p className="text-[10px] font-semibold text-muted-foreground uppercase mb-1.5">Learned preferences</p>
                        <div className="flex flex-wrap gap-1.5">
                          {Object.entries(memPrefs).map(([k, v]) => (
                            <span key={k} className="px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-[10px] text-amber-300">
                              {k}: <span className="text-amber-200 font-medium">{v}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Footer actions */}
                    <div className="border-t border-white/[0.04] px-4 py-2 flex items-center gap-2">
                      <button
                        onClick={fetchMemory}
                        className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <RefreshCw className="w-2.5 h-2.5" />
                        Refresh
                      </button>
                      <button
                        onClick={async () => {
                          setMemClearing(true);
                          await clearOldMemories(30);
                          await fetchMemory();
                          addLog("info", "Old memories cleared (>30 days).");
                          setMemClearing(false);
                        }}
                        disabled={memClearing}
                        className="ml-auto flex items-center gap-1 text-[10px] text-red-400/60 hover:text-red-400 transition-colors disabled:opacity-40"
                      >
                        {memClearing ? <RefreshCw className="w-2.5 h-2.5 animate-spin" /> : null}
                        Clear old (&gt;30d)
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* ── Agent log ──────────────────────────────────────────── */}
              <div className="space-y-2 flex-1">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                    Live Agent Log
                  </label>
                  <button
                    onClick={clearLogs}
                    className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Clear
                  </button>
                </div>
                <AgentLog logs={logs} isRunning={isRunning} onSpeak={speakText} />
              </div>
            </div>

            {/* ═══ RIGHT COLUMN ══════════════════════════════════════════ */}
            <div className="flex flex-col gap-5 px-5 py-5 overflow-y-auto">

              {/* ── Screenshot preview ─────────────────────────────────── */}
              <ScreenshotPreview
                screenshotUrl={screenshotUrl}
                onCapture={url => {
                  setScreenshotUrl(url);
                  addLog("success", "Screenshot captured.");
                }}
              />

              {/* ── Last action card ───────────────────────────────────── */}
              <div className="space-y-2">
                <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Last Action
                </label>
                <div className="rounded-xl bg-[#0d0d12] border border-white/[0.06] p-4 min-h-[80px]">
                  {lastAction ? (
                    <pre className="text-[11px] text-violet-300 font-mono whitespace-pre-wrap break-all leading-relaxed">
                      {JSON.stringify(lastAction, null, 2)}
                    </pre>
                  ) : (
                    <p className="text-[12px] text-slate-600">No action executed yet.</p>
                  )}
                </div>
              </div>

              {/* ── Backend status card ────────────────────────────────── */}
              <div className="space-y-2">
                <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Backend Status
                </label>
                <div className="rounded-xl bg-[#0d0d12] border border-white/[0.06] overflow-hidden">
                  {[
                    {
                      label: "FastAPI",
                      state: backend.fastapi,
                      icon: backend.fastapi === "online" ? Wifi : WifiOff,
                      detail: backend.fastapi === "online" ? "localhost:8000" : "Not reachable",
                    },
                    {
                      label: "Ollama LLM",
                      state: backend.ollama,
                      icon: Cpu,
                      detail: backend.ollama === "online" ? "localhost:11434" : "Not running",
                    },
                    {
                      label: "Active model",
                      state: backend.ollama,
                      icon: Layers,
                      detail: backend.model,
                    },
                  ].map((row, i) => (
                    <div
                      key={row.label}
                      className={`flex items-center gap-3 px-4 py-3 ${i > 0 ? "border-t border-white/[0.04]" : ""} hover:bg-white/[0.02] transition-colors`}
                    >
                      <row.icon className={`w-3.5 h-3.5 shrink-0 ${
                        row.state === "online" ? "text-emerald-400" :
                        row.state === "checking" ? "text-amber-400" : "text-red-400"
                      }`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-[12px] font-medium text-foreground">{row.label}</p>
                        <p className="text-[10px] text-muted-foreground truncate">{row.detail}</p>
                      </div>
                      <StatusDot state={row.state as "online" | "offline" | "checking"} />
                    </div>
                  ))}
                </div>

                <button
                  onClick={checkStatus}
                  className="w-full py-2 rounded-xl border border-white/[0.06] text-[11px] text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all flex items-center justify-center gap-1.5"
                >
                  <RefreshCw className="w-3 h-3" />
                  Refresh status
                </button>
              </div>

            </div>
          </div>
        </div>
      </div>
    </>
  );
}
