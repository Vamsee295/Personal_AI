"use client";
import { useState } from "react";
import { Plus, X, Sparkles, Calendar, ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

interface Task {
  id: number;
  text: string;
  group: "Today" | "Tomorrow" | "Upcoming";
  badges: { label: string; variant: "destructive" | "default" | "secondary" | "outline" }[];
  done: boolean;
}

const initialTasks: Task[] = [
  { id: 1, text: "Submit assignment by 8 PM", group: "Today", badges: [{ label: "High", variant: "destructive" }, { label: "Work", variant: "default" }], done: false },
  { id: 2, text: "Team meeting at 5 PM", group: "Today", badges: [{ label: "Work", variant: "default" }], done: false },
  { id: 3, text: "Push code to GitHub", group: "Today", badges: [{ label: "Work", variant: "default" }], done: false },
  { id: 4, text: "Review PR #42", group: "Today", badges: [{ label: "Done", variant: "outline" }], done: true },
  { id: 5, text: "Call Rahul", group: "Tomorrow", badges: [{ label: "Personal", variant: "secondary" }], done: false },
  { id: 6, text: "Pay electricity bill", group: "Tomorrow", badges: [{ label: "Personal", variant: "secondary" }], done: false },
  { id: 7, text: "Update portfolio", group: "Upcoming", badges: [{ label: "Personal", variant: "secondary" }], done: false },
];

const groups: Task["group"][] = ["Today", "Tomorrow", "Upcoming"];

const groupColors: Record<Task["group"], string> = {
  Today: "text-primary",
  Tomorrow: "text-warning",
  Upcoming: "text-info",
};

const Tasks = () => {
  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [showAdd, setShowAdd] = useState(false);
  const [newText, setNewText] = useState("");
  const [newGroup, setNewGroup] = useState<Task["group"]>("Today");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const toggle = (id: number) => setTasks((p) => p.map((t) => t.id === id ? { ...t, done: !t.done } : t));
  const remove = (id: number) => setTasks((p) => p.filter((t) => t.id !== id));
  const addTask = () => {
    if (!newText.trim()) return;
    setTasks((p) => [...p, { id: Date.now(), text: newText.trim(), group: newGroup, badges: [{ label: newGroup === "Today" ? "Work" : "Personal", variant: newGroup === "Today" ? "default" : "secondary" }], done: false }]);
    setNewText("");
    setShowAdd(false);
  };
  const toggleGroup = (g: string) => setCollapsed((p) => ({ ...p, [g]: !p[g] }));

  const pendingToday = tasks.filter(t => t.group === "Today" && !t.done).length;

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-base font-semibold text-foreground">Tasks</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {pendingToday} task{pendingToday !== 1 ? "s" : ""} pending today
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary border border-border text-[13px] text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
            <Calendar className="w-3.5 h-3.5" />
            Calendar view
          </button>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-[13px] font-medium hover:bg-primary/90 transition-all"
            style={{ boxShadow: "0 0 14px rgba(124,80,255,0.3)" }}
          >
            <Plus className="w-3.5 h-3.5" />
            Add task
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-8 py-6 space-y-5">
        {/* Add task form */}
        {showAdd && (
          <div className="bg-card border border-primary/30 rounded-xl p-4 flex flex-col gap-3 animate-fade-slide-up"
            style={{ boxShadow: "0 0 20px rgba(124,80,255,0.08)" }}>
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-[13px] font-medium text-foreground">New task</span>
            </div>
            <input
              autoFocus
              value={newText}
              onChange={(e) => setNewText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") addTask(); if (e.key === "Escape") setShowAdd(false); }}
              placeholder="What needs to be done?"
              className="bg-secondary border border-border rounded-lg px-3 py-2 text-[13px] text-foreground outline-none placeholder:text-muted-foreground focus:border-primary/40 transition-colors"
            />
            <div className="flex items-center gap-3">
              <select
                value={newGroup}
                onChange={(e) => setNewGroup(e.target.value as Task["group"])}
                className="bg-secondary border border-border rounded-lg px-3 py-1.5 text-[12px] text-foreground outline-none cursor-pointer"
              >
                {groups.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
              <div className="flex gap-2 ml-auto">
                <button onClick={() => setShowAdd(false)} className="px-3 py-1.5 rounded-lg border border-border text-[13px] text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">Cancel</button>
                <button onClick={addTask} className="px-4 py-1.5 rounded-lg bg-primary text-primary-foreground text-[13px] font-medium hover:bg-primary/90 transition-colors">Add</button>
              </div>
            </div>
          </div>
        )}

        {/* Groups */}
        {groups.map((group) => {
          const groupTasks = tasks.filter((t) => t.group === group);
          if (groupTasks.length === 0) return null;
          const isCollapsed = collapsed[group];
          const done = groupTasks.filter(t => t.done).length;
          return (
            <div key={group}>
              <button
                className="flex items-center gap-2 mb-2 w-full text-left"
                onClick={() => toggleGroup(group)}
              >
                <span className={cn("text-[11px] font-semibold uppercase tracking-wider", groupColors[group])}>{group}</span>
                <span className="text-[11px] text-muted-foreground">— {done}/{groupTasks.length} done</span>
                <ChevronDown className={cn("w-3.5 h-3.5 text-muted-foreground ml-auto transition-transform", isCollapsed && "-rotate-90")} />
              </button>
              {!isCollapsed && (
                <div className="bg-card border border-border rounded-xl overflow-hidden">
                  {groupTasks.map((t) => (
                    <div key={t.id} className="flex items-center gap-3 px-5 py-3.5 border-b border-border/50 last:border-b-0 group hover:bg-accent/30 transition-colors">
                      <Checkbox
                        checked={t.done}
                        onCheckedChange={() => toggle(t.id)}
                        className="data-[state=checked]:bg-primary data-[state=checked]:border-primary shrink-0"
                      />
                      <span className={cn("text-[13px] flex-1", t.done ? "line-through text-muted-foreground" : "text-foreground")}>
                        {t.text}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {t.badges.map((b) => (
                          <Badge key={b.label} variant={b.variant} className="text-[10px] px-1.5 py-0">{b.label}</Badge>
                        ))}
                        <button
                          onClick={() => remove(t.id)}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-destructive/20 transition-all ml-1"
                        >
                          <X className="w-3 h-3 text-muted-foreground hover:text-destructive" />
                        </button>
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

export default Tasks;
