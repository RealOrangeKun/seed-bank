import { Outlet } from "react-router-dom";

import { ForbiddenState } from "@/components/shared/states";
import { hasRole, useAuth } from "@/features/auth/use-auth";
import type { Role } from "@/lib/api/types";

/** Gate a subtree to specific roles (admin always passes). */
export function RoleRoute({ allow }: { allow: Role[] }) {
  const { user } = useAuth();
  if (!hasRole(user, allow)) {
    return <ForbiddenState />;
  }
  return <Outlet />;
}
