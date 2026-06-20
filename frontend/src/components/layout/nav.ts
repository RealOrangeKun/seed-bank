import {
  FlaskConical,
  KeyRound,
  LayoutDashboard,
  ScanLine,
  Boxes,
  Database,
  GitBranch,
  Images,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { Role } from "@/lib/api/types";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Roles allowed to see this item; empty = everyone authenticated. */
  roles?: Role[];
}

export interface NavSection {
  heading: string;
  items: NavItem[];
}

export const NAV_SECTIONS: NavSection[] = [
  {
    heading: "Analyze",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/analyze", label: "New analysis", icon: ScanLine },
      { to: "/batches", label: "Scan history", icon: Images },
    ],
  },
  {
    heading: "ML platform",
    items: [
      {
        to: "/models",
        label: "Models",
        icon: Boxes,
        roles: ["ai_developer", "admin"],
      },
      {
        to: "/datasets",
        label: "Datasets",
        icon: Database,
        roles: ["ai_developer", "admin"],
      },
      {
        to: "/experiments",
        label: "Experiments",
        icon: FlaskConical,
        roles: ["ai_developer", "admin"],
      },
      {
        to: "/traffic",
        label: "Traffic splits",
        icon: GitBranch,
        roles: ["admin"],
      },
    ],
  },
  {
    heading: "Account",
    items: [
      { to: "/users", label: "Users", icon: Users, roles: ["admin"] },
      { to: "/api-keys", label: "API keys", icon: KeyRound },
    ],
  },
];
