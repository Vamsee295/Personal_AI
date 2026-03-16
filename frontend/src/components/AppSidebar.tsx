import { LayoutDashboard, Mic, MessageSquare, CheckSquare, Phone, FolderOpen, Monitor, Settings, Terminal } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/router";
import { cn } from "@/lib/utils";

const mainNav = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "Voice Assistant", url: "/voice", icon: Mic },
  { title: "Chat", url: "/chat", icon: MessageSquare },
  { title: "Tasks", url: "/tasks", icon: CheckSquare },
  { title: "Call Logs", url: "/calls", icon: Phone },
  { title: "Files", url: "/files", icon: FolderOpen },
  { title: "Screen AI", url: "/screen-ai", icon: Monitor },
];

export function AppSidebar() {
  const router = useRouter();

  const isActive = (url: string) => {
    if (url === "/") return router.pathname === "/";
    return router.pathname.startsWith(url);
  };

  return (
    <aside className="w-[220px] h-full bg-sidebar border-r border-sidebar-border flex flex-col shrink-0">
      {/* Brand */}
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          {/* Gradient logo mark */}
          <div className="relative w-8 h-8 rounded-xl flex items-center justify-center shrink-0
            bg-gradient-to-br from-violet-600 to-blue-500 shadow-lg"
            style={{ boxShadow: "0 0 16px rgba(124,80,255,0.4)" }}>
            <Terminal className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="text-sm font-semibold text-foreground">Vamsee AI</div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-status-pulse" />
              <span className="text-[10px] text-muted-foreground">Online</span>
            </div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2.5 space-y-0.5 overflow-y-auto">
        {mainNav.map((item) => {
          const active = isActive(item.url);
          return (
            <Link
              key={item.url}
              href={item.url}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150 relative group",
                active
                  ? "bg-primary/12 text-foreground border-l-2 border-primary pl-[10px]"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/60"
              )}
              style={active ? { boxShadow: "inset 0 0 20px rgba(124,80,255,0.06)" } : {}}
            >
              <item.icon className={cn("w-4 h-4 shrink-0 transition-colors", active ? "text-primary" : "")} />
              <span>{item.title}</span>
              {item.title === "Dashboard" && (
                <span className="ml-auto w-2 h-2 rounded-full bg-success animate-status-pulse" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Divider + model info */}
      <div className="px-3 py-2.5 border-t border-sidebar-border">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-accent/40 mb-2">
          <div className="w-5 h-5 rounded-md bg-gradient-to-br from-violet-600 to-blue-500 flex items-center justify-center shrink-0">
            <span className="text-[8px] font-bold text-white">Q</span>
          </div>
          <div>
            <p className="text-[10px] font-medium text-foreground">Qwen 2.5 — 7B</p>
            <p className="text-[9px] text-muted-foreground">via Ollama</p>
          </div>
        </div>
      </div>

      {/* Settings at bottom */}
      <div className="px-2.5 pb-3">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150",
            isActive("/settings")
              ? "bg-primary/12 text-foreground border-l-2 border-primary pl-[10px]"
              : "text-muted-foreground hover:text-foreground hover:bg-accent/60"
          )}
        >
          <Settings className={cn("w-4 h-4 shrink-0", isActive("/settings") ? "text-primary" : "")} />
          <span>Settings</span>
        </Link>
      </div>
    </aside>
  );
}
