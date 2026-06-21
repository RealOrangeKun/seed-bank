import { NavLink } from "react-router-dom";

import { hasRole, useAuth } from "@/features/auth/use-auth";
import { cn } from "@/lib/utils";

import { NAV_SECTIONS } from "./nav";

function Brand() {
  return (
    <div className="flex items-center gap-2 px-2 py-1">
      <img src="/seed.svg" alt="" className="h-7 w-7" />
      <div className="leading-tight">
        <div className="text-sm font-semibold">Seed-Bank</div>
        <div className="text-[11px] text-muted-foreground">Seed intelligence</div>
      </div>
    </div>
  );
}

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();

  return (
    <nav className="flex h-full flex-col gap-6 p-3">
      <Brand />
      <div className="flex flex-col gap-5">
        {NAV_SECTIONS.map((section) => {
          const items = section.items.filter(
            (item) => !item.roles || hasRole(user, item.roles),
          );
          if (items.length === 0) return null;
          return (
            <div key={section.heading} className="space-y-1">
              <p className="px-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                {section.heading}
              </p>
              {items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    )
                  }
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </NavLink>
              ))}
            </div>
          );
        })}
      </div>
    </nav>
  );
}
