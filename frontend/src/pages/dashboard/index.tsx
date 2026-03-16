"use client";
import { useState } from "react";
import { CheckSquare, Phone, FolderOpen, Activity, Plus, X, ChevronRight, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";

const statsConfig = [
  { label: "Tasks today", value: "4", icon: CheckSquare, color: "text-primary", bg: "bg-primary/10", glow: "rgba(124,80,255,0.2)" },
  { label: "Calls handled", value: "3", icon: Phone, color: "text-info", bg: "bg-info/10", glow: "rgba(59,130,246,0.2)" },
  { label: "Files organised", value: "18", icon: FolderOpen, color: "text-warning", bg: "bg-warning/10", glow: "rgba(245,158,11,0.2)" },
  { label: "AI uptime", value: "99%", icon: Activity, color: "text-success", bg: "bg-success/10", glow: "rgba(34,197,94,0.2)" },
];

const activities = [
  { avatar: "PC", color: "from-blue-600 to-blue-500", text: "Opened VS Code", sub: "PC automation", time: "2m ago" },
  { avatar: "FL", color: "from-amber-600 to-amber-500", text: "Organised Downloads folder", sub: "18 files sorted", time: "14m ago" },
  { avatar: "CL", color: "from-purple-600 to-purple-500", text: "Answered call from Rahul", sub: "Auto-answered · logged summary", time: "1h ago" },
  { avatar: "AI", color: "from-emerald-600 to-emerald-500", text: "Detected Python error on screen", sub: "Python NameError fixed", time: "2h ago" },
  { avatar: "PC", color: "from-blue-600 to-blue-500", text: "Set reminder: Team meeting 5 PM", sub: "Calendar updated", time: "3h ago" },
];

interface Task {
  id: number;
  text: string;
  badges: { label: string; variant: "destructive" | "default" | "secondary" | "outline" }[];
  done: boolean;
}

const initialTasks: Task[] = [
  { id: 1, text: "Submit assignment by 8 PM", badges: [{ label: "High", variant: "destructive" }, { label: "Work", variant: "default" }], done: false },
  { id: 2, text: "Team meeting at 5 PM", badges: [{ label: "Work", variant: "default" }], done: false },
  { id: 3, text: "Call Rahul tomorrow", badges: [{ label: "Personal", variant: "secondary" }], done: false },
  { id: 4, text: "Review PR #42", badges: [{ label: "Done", variant: "outline" }], done: true },
];

const Dashboard = () => {
  const now = new Date();
  const greeting = now.getHours() < 12 ? "Good morning" : now.getHours() < 18 ? "Good afternoon" : "Good evening";
  const dateStr = now.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });

  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [showAddTask, setShowAddTask] = useState(false);
  const [newTaskText, setNewTaskText] = useState("");

  const toggleTask = (id: number) => {
    setTasks((prev) => prev.map((t) => t.id === id ? { ...t, done: !t.done } : t));
  };

  const addTask = () => {
    if (!newTaskText.trim()) return;
    setTasks((prev) => [
      ...prev,
      { id: Date.now(), text: newTaskText.trim(), badges: [{ label: "Work", variant: "default" }], done: false },
    ]);
    setNewTaskText("");
    setShowAddTask(false);
  };

  const deleteTask = (id: number) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border flex items-center justify-between shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <h1 className="text-xl font-semibold text-foreground">{greeting}, Vamsee</h1>
            <span className="text-lg">👋</span>
          </div>
          <p className="text-xs text-muted-foreground">
            {dateStr} ·{" "}
            <span className="inline-flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-status-pulse inline-block" />
              <span className="text-success">AI is online</span>
            </span>
          </p>
        </div>
        <button
          onClick={() => setShowAddTask(true)}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-[13px] font-medium hover:bg-primary/90 transition-all duration-150"
          style={{ boxShadow: "0 0 16px rgba(124,80,255,0.3)" }}
        >
          <Plus className="w-3.5 h-3.5" />
          New task
        </button>
      </div>

      {/* Content area — scrollable */}
      <div className="flex-1 overflow-auto px-8 py-6 space-y-6">
        {/* Stat cards */}
        <div className="grid grid-cols-4 gap-4">
          {statsConfig.map((s) => (
            <div
              key={s.label}
              className="bg-card border border-border rounded-xl p-5 hover:border-primary/30 transition-colors duration-200"
              style={{ boxShadow: `0 0 20px ${s.glow}` }}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-muted-foreground">{s.label}</span>
                <div className={`w-8 h-8 rounded-lg ${s.bg} flex items-center justify-center`}>
                  <s.icon className={`w-4 h-4 ${s.color}`} />
                </div>
              </div>
              <div className="text-3xl font-bold text-foreground">{s.value}</div>
            </div>
          ))}
        </div>

        {/* Add task inline */}
        {showAddTask && (
          <div className="flex items-center gap-3 bg-card border border-primary/40 rounded-xl p-4 animate-fade-slide-up"
            style={{ boxShadow: "0 0 20px rgba(124,80,255,0.1)" }}>
            <Sparkles className="w-4 h-4 text-primary shrink-0" />
            <input
              autoFocus
              value={newTaskText}
              onChange={(e) => setNewTaskText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") addTask(); if (e.key === "Escape") setShowAddTask(false); }}
              placeholder="Describe your task..."
              className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            />
            <button onClick={addTask} className="px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors">
              Add
            </button>
            <button onClick={() => setShowAddTask(false)} className="p-1 rounded-md hover:bg-accent transition-colors">
              <X className="w-3.5 h-3.5 text-muted-foreground" />
            </button>
          </div>
        )}

        {/* Main grid */}
        <div className="grid grid-cols-5 gap-5">
          {/* Recent Activity */}
          <div className="col-span-3">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-foreground">Recent activity</h2>
              <button className="text-[11px] text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
                View all <ChevronRight className="w-3 h-3" />
              </button>
            </div>
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              {activities.map((a, i) => (
                <div
                  key={i}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-accent/40 transition-colors duration-100 border-b border-border/50 last:border-b-0"
                >
                  <div className={`w-9 h-9 rounded-full bg-gradient-to-br ${a.color} flex items-center justify-center text-[10px] font-bold text-white shrink-0 shadow-sm`}>
                    {a.avatar}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] text-foreground font-medium truncate">{a.text}</p>
                    <p className="text-[11px] text-muted-foreground truncate">{a.sub}</p>
                  </div>
                  <span className="text-[11px] text-muted-foreground whitespace-nowrap">{a.time}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Today's tasks */}
          <div className="col-span-2">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-foreground">Today's tasks</h2>
              <span className="text-[11px] text-muted-foreground">{tasks.filter(t => !t.done).length} pending</span>
            </div>
            <div className="bg-card border border-border rounded-xl overflow-hidden">
              {tasks.map((t) => (
                <div key={t.id} className="flex items-center gap-3 px-5 py-3.5 border-b border-border/50 last:border-b-0 group hover:bg-accent/40 transition-colors">
                  <Checkbox
                    checked={t.done}
                    onCheckedChange={() => toggleTask(t.id)}
                    className="data-[state=checked]:bg-primary data-[state=checked]:border-primary shrink-0"
                  />
                  <span className={`text-[13px] flex-1 transition-all ${t.done ? "line-through text-muted-foreground" : "text-foreground"}`}>
                    {t.text}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {t.badges.map((b) => (
                      <Badge key={b.label} variant={b.variant} className="text-[10px] px-1.5 py-0">{b.label}</Badge>
                    ))}
                    <button
                      onClick={() => deleteTask(t.id)}
                      className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-destructive/20 transition-all"
                    >
                      <X className="w-3 h-3 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>
                </div>
              ))}
              {tasks.length === 0 && (
                <div className="px-5 py-8 text-center text-[13px] text-muted-foreground">
                  All tasks complete! 🎉
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
