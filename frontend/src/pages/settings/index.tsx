"use client";
import { useState } from "react";
import { Save, CheckCircle, Sparkles } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface Feature {
  key: string;
  label: string;
  description: string;
  default: boolean;
}

const features: Feature[] = [
  { key: "voice", label: "Voice assistant", description: "Enable voice commands via microphone", default: true },
  { key: "bubble", label: "Floating AI bubble", description: "Show quick-access bubble on screen", default: true },
  { key: "calls", label: "Auto-answer calls", description: "Automatically answer incoming VoIP calls", default: true },
  { key: "screen", label: "Screen AI", description: "Capture and analyse screen content", default: false },
  { key: "files", label: "File auto-organise", description: "Automatically sort files in Downloads", default: true },
  { key: "thinking", label: "AI thinking indicator", description: "Show processing animation in UI", default: true },
];

const SettingsPage = () => {
  const [name, setName] = useState("Ultron");
  const [savedName, setSavedName] = useState("Ultron");
  const [nameSaved, setNameSaved] = useState(false);
  const [toggles, setToggles] = useState<Record<string, boolean>>(
    Object.fromEntries(features.map((f) => [f.key, f.default]))
  );
  const [justToggled, setJustToggled] = useState<string | null>(null);

  const handleNameSave = () => {
    setSavedName(name);
    setNameSaved(true);
    setTimeout(() => setNameSaved(false), 2000);
  };

  const handleToggle = (key: string, val: boolean) => {
    setToggles((p) => ({ ...p, [key]: val }));
    setJustToggled(key);
    setTimeout(() => setJustToggled(null), 1500);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border shrink-0">
        <h1 className="text-base font-semibold text-foreground">Settings</h1>
        <p className="text-xs text-muted-foreground mt-0.5">Configure your personal AI assistant</p>
      </div>

      <div className="flex-1 overflow-auto px-8 py-6 space-y-5">
        {/* AI Model card */}
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            <h2 className="text-[13px] font-semibold text-foreground">AI Model</h2>
          </div>
          <div className="px-5 py-5 space-y-5">
            {/* Model info */}
            <div className="flex items-center justify-between p-4 bg-secondary/50 rounded-xl border border-border">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center">
                  <span className="text-[12px] font-bold text-white">Q</span>
                </div>
                <div>
                  <p className="text-[13px] font-medium text-foreground">Qwen2.5 — 7B</p>
                  <p className="text-[11px] text-muted-foreground">via Ollama · localhost:11434</p>
                </div>
              </div>
              <Badge className="bg-success/20 text-success border-0 text-[10px] px-2.5">
                <span className="w-1.5 h-1.5 rounded-full bg-success animate-status-pulse inline-block mr-1.5" />
                Running
              </Badge>
            </div>

            {/* Assistant name */}
            <div>
              <label className="text-[12px] font-medium text-muted-foreground block mb-2">Assistant name</label>
              <div className="flex items-center gap-3">
                <input
                  value={name}
                  onChange={(e) => { setName(e.target.value); setNameSaved(false); }}
                  onKeyDown={(e) => e.key === "Enter" && handleNameSave()}
                  className="flex-1 max-w-xs h-9 px-3 rounded-lg bg-secondary border border-border text-[13px] text-foreground outline-none focus:border-primary/50 transition-colors placeholder:text-muted-foreground"
                />
                <button
                  onClick={handleNameSave}
                  disabled={name === savedName}
                  className={cn(
                    "flex items-center gap-1.5 px-4 h-9 rounded-lg text-[13px] font-medium transition-all duration-200",
                    nameSaved
                      ? "bg-success/20 text-success border border-success/30"
                      : "bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40"
                  )}
                >
                  {nameSaved
                    ? <><CheckCircle className="w-3.5 h-3.5" /> Saved!</>
                    : <><Save className="w-3.5 h-3.5" /> Save</>}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Features card */}
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-[13px] font-semibold text-foreground">Features</h2>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {Object.values(toggles).filter(Boolean).length} of {features.length} enabled
            </p>
          </div>
          <div className="divide-y divide-border">
            {features.map((f) => {
              const isOn = toggles[f.key];
              const justChanged = justToggled === f.key;
              return (
                <div
                  key={f.key}
                  className={cn(
                    "flex items-center justify-between px-5 py-4 transition-colors duration-300",
                    justChanged && (isOn ? "bg-success/5" : "bg-muted/30")
                  )}
                >
                  <div className="flex-1 min-w-0 mr-4">
                    <p className="text-[13px] font-medium text-foreground">{f.label}</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">{f.description}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    {justChanged && (
                      <span className={cn(
                        "text-[10px] font-medium animate-fade-slide-up",
                        isOn ? "text-success" : "text-muted-foreground"
                      )}>
                        {isOn ? "Enabled" : "Disabled"}
                      </span>
                    )}
                    <Switch
                      checked={isOn}
                      onCheckedChange={(val) => handleToggle(f.key, val)}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Danger zone */}
        <div className="bg-card border border-destructive/20 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-destructive/15">
            <h2 className="text-[13px] font-semibold text-destructive">Danger zone</h2>
          </div>
          <div className="px-5 py-4 flex items-center justify-between">
            <div>
              <p className="text-[13px] text-foreground">Reset all data</p>
              <p className="text-[11px] text-muted-foreground">Clear all call logs, task history, and AI memory</p>
            </div>
            <button className="px-4 py-2 rounded-lg border border-destructive/40 text-destructive text-[13px] font-medium hover:bg-destructive/10 transition-colors">
              Reset
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
