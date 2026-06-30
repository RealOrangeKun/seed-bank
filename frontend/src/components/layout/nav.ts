import {
  FlaskConical,
  KeyRound,
  LayoutDashboard,
  ScanLine,
  Boxes,
  ChartColumn,
  Database,
  GitCompareArrows,
  Images,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { TranslationKey } from "@/i18n/dictionaries/en";
import type { Role } from "@/lib/api/types";

export interface NavItem {
  to: string;
  labelKey: TranslationKey;
  icon: LucideIcon;
  /** Roles allowed to see this item; empty = everyone authenticated. */
  roles?: Role[];
}

export interface NavSection {
  headingKey: TranslationKey;
  items: NavItem[];
}

export const NAV_SECTIONS: NavSection[] = [
  {
    headingKey: "nav.section.analyze",
    items: [
      { to: "/dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard },
      { to: "/analyze", labelKey: "nav.analyze", icon: ScanLine },
      { to: "/batches", labelKey: "nav.batches", icon: Images },
      { to: "/analytics", labelKey: "nav.analytics", icon: ChartColumn },
      { to: "/compare", labelKey: "nav.compare", icon: GitCompareArrows },
    ],
  },
  {
    headingKey: "nav.section.mlPlatform",
    items: [
      {
        to: "/models",
        labelKey: "nav.models",
        icon: Boxes,
        roles: ["ai_developer", "admin"],
      },
      {
        to: "/datasets",
        labelKey: "nav.datasets",
        icon: Database,
        roles: ["ai_developer", "admin"],
      },
      {
        to: "/experiments",
        labelKey: "nav.experiments",
        icon: FlaskConical,
        roles: ["ai_developer", "admin"],
      },
    ],
  },
  {
    headingKey: "nav.section.account",
    items: [
      { to: "/users", labelKey: "nav.users", icon: Users, roles: ["admin"] },
      { to: "/api-keys", labelKey: "nav.apiKeys", icon: KeyRound },
    ],
  },
];
