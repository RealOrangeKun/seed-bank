import { useState } from "react";
import { Outlet } from "react-router-dom";

import { Dialog, DialogContent } from "@/components/ui/dialog";

import { SidebarNav } from "./sidebar";
import { Topbar } from "./topbar";

/** Authenticated app frame: fixed sidebar on desktop, drawer on mobile. */
export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-64 shrink-0 border-r bg-surface md:block">
        <div className="sticky top-0 h-screen overflow-y-auto">
          <SidebarNav />
        </div>
      </aside>

      <Dialog open={mobileOpen} onOpenChange={setMobileOpen}>
        <DialogContent className="left-0 top-0 h-full max-w-64 translate-x-0 translate-y-0 rounded-none p-0 sm:rounded-none">
          <SidebarNav onNavigate={() => setMobileOpen(false)} />
        </DialogContent>
      </Dialog>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenuClick={() => setMobileOpen(true)} />
        <main className="flex-1 p-4 sm:p-6">
          <div className="mx-auto w-full max-w-6xl space-y-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
