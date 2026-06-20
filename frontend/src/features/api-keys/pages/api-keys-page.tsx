import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle, KeyRound, Plus } from "lucide-react";
import { useState } from "react";
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
import { usePagination } from "@/hooks/use-pagination";
import type { ApiKeyOut } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { applyApiError } from "@/lib/form";

import { useApiKeys, useCreateApiKey, useRevokeApiKey } from "../api";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  scopes: z.string().optional().or(z.literal("")),
  expiresAt: z.string().optional().or(z.literal("")),
});
type FormValues = z.infer<typeof schema>;

/** Parse a comma-separated scopes string into a trimmed, de-empty list. */
function parseScopes(raw: string | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export function ApiKeysPage() {
  const pagination = usePagination(20);
  const query = useApiKeys({ page: pagination.page, pageSize: pagination.pageSize });

  const [createOpen, setCreateOpen] = useState(false);
  const [createdKey, setCreatedKey] = useState<ApiKeyOut | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<ApiKeyOut | null>(null);

  const create = useCreateApiKey();
  const revoke = useRevokeApiKey();

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
        title="API keys"
        description="Programmatic access tokens for the Seed-Bank API."
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" /> Create key
          </Button>
        }
      />

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No API keys yet"
          description="Create a key to authenticate programmatic requests to the API."
          action={
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" /> Create key
            </Button>
          }
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Prefix</TableHead>
                  <TableHead>Scopes</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Last used</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
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
                          <Badge variant="destructive">revoked</Badge>
                        ) : (
                          <Badge variant="success">active</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {revoked ? null : (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                            onClick={() => setRevokeTarget(key)}
                          >
                            Revoke
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
            <DialogTitle>Create API key</DialogTitle>
            <DialogDescription>
              The plaintext key is shown only once after creation.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <Field
              id="name"
              label="Name"
              required
              error={form.formState.errors.name?.message}
            >
              <Input id="name" placeholder="CI pipeline" {...form.register("name")} />
            </Field>
            <Field
              id="scopes"
              label="Scopes"
              hint="Comma-separated, e.g. analyze:write, models:read"
              error={form.formState.errors.scopes?.message}
            >
              <Input id="scopes" placeholder="analyze:write, models:read" {...form.register("scopes")} />
            </Field>
            <Field
              id="expiresAt"
              label="Expires at"
              hint="Optional; leave blank for a non-expiring key"
              error={form.formState.errors.expiresAt?.message}
            >
              <Input id="expiresAt" type="datetime-local" {...form.register("expiresAt")} />
            </Field>
            <DialogFooter>
              <DialogClose asChild>
                <Button type="button" variant="outline">
                  Cancel
                </Button>
              </DialogClose>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? <Spinner /> : <KeyRound className="h-4 w-4" />}
                Create key
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
            <DialogTitle>Key created</DialogTitle>
            <DialogDescription>
              Copy this key now — it is shown once and can never be retrieved again.
            </DialogDescription>
          </DialogHeader>

          {createdKey ? (
            <div className="space-y-4">
              <div className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning-foreground">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  Store this key securely. Once you close this dialog it will not be
                  shown again.
                </span>
              </div>
              {createdKey.key ? (
                <div className="flex items-center justify-between gap-2 rounded-md border bg-muted/40 p-3">
                  <code className="break-all font-mono text-sm">{createdKey.key}</code>
                  <CopyButton value={createdKey.key} label="Copy API key" />
                </div>
              ) : null}
            </div>
          ) : null}

          <DialogFooter>
            <Button type="button" onClick={() => setCreatedKey(null)}>
              Done
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
            <DialogTitle>Revoke API key</DialogTitle>
            <DialogDescription>
              {revokeTarget
                ? `Revoking "${revokeTarget.name}" immediately invalidates it. This cannot be undone.`
                : null}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button
              type="button"
              variant="destructive"
              disabled={revoke.isPending}
              onClick={onRevoke}
            >
              {revoke.isPending ? <Spinner /> : null}
              Revoke
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
