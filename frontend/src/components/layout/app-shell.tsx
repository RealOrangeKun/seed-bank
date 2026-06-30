import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/utils";

import { SidebarNav } from "./sidebar";
import { Topbar } from "./topbar";

/** Authenticated app frame: fixed sidebar on desktop, drawer on mobile. */
export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { dir } = useI18n();
  const location = useLocation();

  // Pin the drawer to the inline-start edge in both directions (left in LTR,
  // right in RTL). Important modifiers beat the dialog's centering defaults.
  const drawerSide = dir === "rtl" ? "!right-0 !left-auto" : "!left-0 !right-auto";

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-64 shrink-0 border-r bg-surface md:block">
        <div className="sticky top-0 h-screen overflow-y-auto">
          <SidebarNav />
        </div>
      </aside>

      <Dialog open={mobileOpen} onOpenChange={setMobileOpen}>
        <DialogContent
          // No exit animation: closing the drawer happens in the same commit as
          // the nav click's route change, which can fire a lazy-route Suspense
          // fallback that orphans the overlay's `animationend` and leaves it
          // stuck dimming the screen. Synchronous unmount sidesteps that race.
          animateClose={false}
          className={cn(
            "!top-0 h-full max-w-64 !translate-x-0 !translate-y-0 rounded-none p-0 sm:rounded-none",
            drawerSide,
          )}
        >
          <SidebarNav onNavigate={() => setMobileOpen(false)} />
        </DialogContent>
      </Dialog>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenuClick={() => setMobileOpen(true)} />
        <main className="flex-1 p-4 sm:p-6">
          {/* Re-key on path so each navigation gets a gentle fade+rise — calmer
              than an instant content swap. */}
          <div
            key={location.pathname}
            className="mx-auto w-full max-w-6xl space-y-6 duration-300 animate-in fade-in-0 slide-in-from-bottom-1"
          >
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
