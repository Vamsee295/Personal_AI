import { AppSidebar } from "./AppSidebar";
import { FloatingBubble } from "./FloatingBubble";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen flex w-full bg-background overflow-hidden">
      <AppSidebar />
      <main className="flex-1 overflow-auto min-w-0">
        {children}
      </main>
      <FloatingBubble />
    </div>
  );
}
