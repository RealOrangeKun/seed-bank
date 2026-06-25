import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle, KeyRound, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { CopyButton } from "@/components/shared/copy-button";
import { Field } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/shared/pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
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
import { usePagination } from "@/hooks/use-pagination";
import type { ApiKeyOut } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { applyApiError } from "@/lib/form";

import { useApiKeys, useCreateApiKey, useRevokeApiKey } from "../api";

interface FormValues {
  name: string;
  scopes?: string;
  expiresAt?: string;
}

/** Parse a comma-separated scopes string into a trimmed, de-empty list. */
function parseScopes(raw: string | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export function ApiKeysPage() {
  const { t } = useI18n();
  const pagination = usePagination(20);
  const query = useApiKeys({ page: pagination.page, pageSize: pagination.pageSize });

  const [createOpen, setCreateOpen] = useState(false);
  const [createdKey, setCreatedKey] = useState<ApiKeyOut | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<ApiKeyOut | null>(null);

  const create = useCreateApiKey();
  const revoke = useRevokeApiKey();

  const schema = useMemo(
    () =>
      z.object({
        name: z.string().min(1, t("apiKeys.nameRequired")),
        scopes: z.string().optional().or(z.literal("")),
        expiresAt: z.string().optional().or(z.literal("")),
      }),
    [t],
  );

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", scopes: "", expiresAt: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const created = await create.mutateAsync({
        name: values.name,
        scopes: parseScopes(values.scopes),
        // datetime-local yields "YYYY-MM-DDTHH:mm"; promote to an ISO string.
        expiresAt: values.expiresAt
          ? new Date(values.expiresAt).toISOString()
          : undefined,
      });
      setCreateOpen(false);
      form.reset();
      setCreatedKey(created);
    } catch (err) {
      applyApiError(err, form.setError);
    }
  });

  const onRevoke = async () => {
    if (!revokeTarget) return;
    try {
      await revoke.mutateAsync(revokeTarget.id);
      setRevokeTarget(null);
    } catch {
      // useRevokeApiKey surfaces failures; keep the dialog open for a retry.
    }
  };

  const rows = query.data?.data ?? [];

  return (
    <>
      <PageHeader
        title={t("apiKeys.title")}
        description={t("apiKeys.description")}
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" /> {t("apiKeys.createKey")}
          </Button>
        }
      />

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : rows.length === 0 ? (
        <EmptyState
          title={t("apiKeys.noKeysTitle")}
          description={t("apiKeys.noKeysDesc")}
          action={
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" /> {t("apiKeys.createKey")}
            </Button>
          }
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("apiKeys.colName")}</TableHead>
                  <TableHead>{t("apiKeys.colPrefix")}</TableHead>
                  <TableHead>{t("apiKeys.colScopes")}</TableHead>
                  <TableHead>{t("apiKeys.colCreated")}</TableHead>
                  <TableHead>{t("apiKeys.colLastUsed")}</TableHead>
                  <TableHead>{t("apiKeys.colStatus")}</TableHead>
                  <TableHead className="text-end">{t("apiKeys.colActions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((key) => {
                  const revoked = Boolean(key.revoked_at);
                  return (
                    <TableRow key={key.id}>
                      <TableCell className="font-medium">{key.name}</TableCell>
                      <TableCell className="font-mono text-xs">{key.prefix}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {key.scopes.length > 0 ? key.scopes.join(", ") : "—"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDateTime(key.created_at)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {key.last_used_at ? formatDateTime(key.last_used_at) : "—"}
                      </TableCell>
                      <TableCell>
                        {revoked ? (
                          <Badge variant="destructive">{t("apiKeys.revoked")}</Badge>
                        ) : (
                          <Badge variant="success">{t("apiKeys.active")}</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-end">
                        {revoked ? null : (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                            onClick={() => setRevokeTarget(key)}
                          >
                            {t("apiKeys.revoke")}
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {query.data ? (
        <Pagination meta={query.data.meta} onPageChange={pagination.setPage} />
      ) : null}

      {/* Create key dialog */}
      <Dialog
        open={createOpen}
        onOpenChange={(open) => {
          setCreateOpen(open);
          if (!open) form.reset();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("apiKeys.createDialogTitle")}</DialogTitle>
            <DialogDescription>{t("apiKeys.createDialogDesc")}</DialogDescription>
          </DialogHeader>
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <Field
              id="name"
              label={t("apiKeys.name")}
              required
              error={form.formState.errors.name?.message}
            >
              <Input
                id="name"
                placeholder={t("apiKeys.namePlaceholder")}
                {...form.register("name")}
              />
            </Field>
            <Field
              id="scopes"
              label={t("apiKeys.scopes")}
              hint={t("apiKeys.scopesHint")}
              error={form.formState.errors.scopes?.message}
            >
              <Input
                id="scopes"
                placeholder={t("apiKeys.scopesPlaceholder")}
                {...form.register("scopes")}
              />
            </Field>
            <Field
              id="expiresAt"
              label={t("apiKeys.expiresAt")}
              hint={t("apiKeys.expiresHint")}
              error={form.formState.errors.expiresAt?.message}
            >
              <Input id="expiresAt" type="datetime-local" {...form.register("expiresAt")} />
            </Field>
            <DialogFooter>
              <DialogClose asChild>
                <Button type="button" variant="outline">
                  {t("common.cancel")}
                </Button>
              </DialogClose>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? <Spinner /> : <KeyRound className="h-4 w-4" />}
                {t("apiKeys.createKey")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Created-key reveal dialog (plaintext shown once) */}
      <Dialog
        open={createdKey !== null}
        onOpenChange={(open) => {
          if (!open) setCreatedKey(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("apiKeys.keyCreated")}</DialogTitle>
            <DialogDescription>{t("apiKeys.keyCreatedDesc")}</DialogDescription>
          </DialogHeader>

          {createdKey ? (
            <div className="space-y-4">
              <div className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning-foreground">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{t("apiKeys.storeSecurely")}</span>
              </div>
              {createdKey.key ? (
                <div className="flex items-center justify-between gap-2 rounded-md border bg-muted/40 p-3">
                  <code className="break-all font-mono text-sm" dir="ltr">
                    {createdKey.key}
                  </code>
                  <CopyButton value={createdKey.key} label={t("apiKeys.copyApiKey")} />
                </div>
              ) : null}
            </div>
          ) : null}

          <DialogFooter>
            <Button type="button" onClick={() => setCreatedKey(null)}>
              {t("common.done")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke confirm dialog */}
      <Dialog
        open={revokeTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRevokeTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("apiKeys.revokeDialogTitle")}</DialogTitle>
            <DialogDescription>
              {revokeTarget
                ? t("apiKeys.revokeDialogDesc", { name: revokeTarget.name })
                : null}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                {t("common.cancel")}
              </Button>
            </DialogClose>
            <Button
              type="button"
              variant="destructive"
              disabled={revoke.isPending}
              onClick={onRevoke}
            >
              {revoke.isPending ? <Spinner /> : null}
              {t("apiKeys.revoke")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
