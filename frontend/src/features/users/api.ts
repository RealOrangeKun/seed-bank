import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, unwrap } from "@/lib/api/client";
import type { Envelope, MeOut, Page, Role, UserListOut } from "@/lib/api/types";

export interface UserListParams {
  page: number;
  pageSize: number;
}

async function listUsers(params: UserListParams): Promise<Page<UserListOut>> {
  const result = await api.GET("/api/v1/users", {
    params: {
      query: {
        page: params.page,
        page_size: params.pageSize,
      },
    },
  });
  return unwrap<Page<UserListOut>>(result);
}

export interface UpdateRoleInput {
  userId: string;
  role: Role;
}

async function updateRole(input: UpdateRoleInput): Promise<MeOut> {
  const result = await api.PATCH("/api/v1/users/{user_id}/role", {
    params: { path: { user_id: input.userId } },
    body: { role: input.role },
  });
  const env = await unwrap<Envelope<MeOut>>(result);
  return env.data;
}

export const userKeys = {
  all: ["users"] as const,
  list: (params: UserListParams) => ["users", "list", params] as const,
};

export function useUsers(params: UserListParams) {
  return useQuery({
    queryKey: userKeys.list(params),
    queryFn: () => listUsers(params),
    placeholderData: (prev) => prev,
  });
}

export function useUpdateRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateRole,
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: userKeys.all });
      toast.success(`Role updated for ${user.email}.`);
    },
  });
}
