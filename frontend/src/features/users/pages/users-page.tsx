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
import { useI18n } from "@/i18n";
import { ROLES } from "@/lib/api/types";
import type { Role, UserListOut } from "@/lib/api/types";
import { humanize } from "@/lib/format";
import { usePagination } from "@/hooks/use-pagination";

import { useUpdateRole, useUsers } from "../api";

interface PendingChange {
  user: UserListOut;
  role: Role;
}

export function UsersPage() {
  const { t } = useI18n();
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
      <PageHeader title={t("users.title")} description={t("users.description")} />

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : users.length === 0 ? (
        <EmptyState title={t("users.empty")} description={t("users.emptyDesc")} />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("field.email")}</TableHead>
                  <TableHead>{t("field.name")}</TableHead>
                  <TableHead>{t("field.role")}</TableHead>
                  <TableHead>{t("users.colVerified")}</TableHead>
                  <TableHead>{t("users.colActive")}</TableHead>
                  <TableHead className="text-end">{t("users.colChangeRole")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.email}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {u.full_name ?? "—"}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={u.role} />
                    </TableCell>
                    <TableCell>
                      <Badge variant={u.is_verified ? "success" : "warning"}>
                        {u.is_verified ? t("users.verified") : t("users.unverified")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={u.is_active ? "success" : "secondary"}>
                        {u.is_active ? t("users.active") : t("users.inactive")}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-end">
                      <Select
                        value={u.role}
                        onValueChange={(value) =>
                          setPending({ user: u, role: value as Role })
                        }
                      >
                        <SelectTrigger className="ms-auto w-40">
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
            <DialogTitle>{t("users.changeRoleTitle")}</DialogTitle>
            <DialogDescription>
              {pending
                ? t("users.changeRoleConfirm", {
                    email: pending.user.email,
                    from: humanize(pending.user.role),
                    to: humanize(pending.role),
                  })
                : null}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPending(null)}
              disabled={updateRole.isPending}
            >
              {t("common.cancel")}
            </Button>
            <Button onClick={confirm} disabled={updateRole.isPending}>
              {updateRole.isPending ? <Spinner /> : null}
              {t("common.confirm")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
