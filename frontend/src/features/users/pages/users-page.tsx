import { useState } from "react";

import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/shared/pagination";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ROLES } from "@/lib/api/types";
import type { Role, UserListOut } from "@/lib/api/types";
import { humanize, shortId } from "@/lib/format";
import { usePagination } from "@/hooks/use-pagination";

import { useUpdateRole, useUsers } from "../api";

interface PendingChange {
  user: UserListOut;
  role: Role;
}

export function UsersPage() {
  const pagination = usePagination(20);
  const query = useUsers({ page: pagination.page, pageSize: pagination.pageSize });
  const updateRole = useUpdateRole();
  const [pending, setPending] = useState<PendingChange | null>(null);

  const users = query.data?.data ?? [];

  const confirm = async () => {
    if (!pending) return;
    try {
      await updateRole.mutateAsync({ userId: pending.user.id, role: pending.role });
      setPending(null);
    } catch {
      // mutation surfaces the error via toast/onError; keep the dialog open.
    }
  };

  return (
    <>
      <PageHeader
        title="Users"
        description="Manage roles and access across the platform."
      />

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : users.length === 0 ? (
        <EmptyState
          title="No users"
          description="No users match the current page."
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Verified</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead className="text-right">Change role</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">
                      {u.email}
                      <span className="ml-2 font-mono text-xs text-muted-foreground">
                        {shortId(u.id)}
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {u.full_name ?? "—"}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={u.role} />
                    </TableCell>
                    <TableCell>
                      <Badge variant={u.is_verified ? "success" : "warning"}>
                        {u.is_verified ? "Verified" : "Unverified"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={u.is_active ? "success" : "secondary"}>
                        {u.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Select
                        value={u.role}
                        onValueChange={(value) =>
                          setPending({ user: u, role: value as Role })
                        }
                      >
                        <SelectTrigger className="ml-auto w-40">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {ROLES.map((role) => (
                            <SelectItem key={role} value={role}>
                              {humanize(role)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {query.data ? (
        <Pagination meta={query.data.meta} onPageChange={pagination.setPage} />
      ) : null}

      <Dialog
        open={pending !== null}
        onOpenChange={(open) => {
          if (!open) setPending(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change role</DialogTitle>
            <DialogDescription>
              {pending ? (
                <>
                  Change <span className="font-medium">{pending.user.email}</span> from{" "}
                  <span className="font-medium">{humanize(pending.user.role)}</span> to{" "}
                  <span className="font-medium">{humanize(pending.role)}</span>?
                </>
              ) : null}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPending(null)}
              disabled={updateRole.isPending}
            >
              Cancel
            </Button>
            <Button onClick={confirm} disabled={updateRole.isPending}>
              {updateRole.isPending ? <Spinner /> : null}
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
