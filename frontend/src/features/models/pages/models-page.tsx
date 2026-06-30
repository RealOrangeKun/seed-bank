import { zodResolver } from "@hookform/resolvers/zod";
import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { Field } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { SeedTypeSelect } from "@/components/shared/resource-select";
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
import { Input } from "@/components/ui/input";
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
import { formatDateTime, humanize } from "@/lib/format";
import { applyApiError } from "@/lib/form";
import { MODEL_BACKENDS, MODEL_KINDS, MODEL_STATUSES } from "@/lib/api/types";
import type { ModelKind, ModelStatus } from "@/lib/api/types";
import { usePagination } from "@/hooks/use-pagination";

import { useModels, useRegisterModel } from "../api";

const ALL = "all";

interface RegisterValues {
  name: string;
  version: string;
  kind: ModelKind;
  backend: (typeof MODEL_BACKENDS)[number];
  artifactUri: string;
  seedTypeId?: string;
}

function RegisterModelDialog() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const register = useRegisterModel();

  const registerSchema = useMemo(
    () =>
      z.object({
        name: z.string().min(1, t("models.nameRequired")),
        version: z.string().min(1, t("models.versionRequired")),
        kind: z.enum(MODEL_KINDS),
        backend: z.enum(MODEL_BACKENDS),
        artifactUri: z.string().min(1, t("models.artifactUriRequired")),
        seedTypeId: z.string().uuid(t("models.uuidInvalid")).optional().or(z.literal("")),
      }),
    [t],
  );

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: "",
      version: "",
      kind: "detection",
      backend: "torch_local",
      artifactUri: "",
      seedTypeId: "",
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const model = await register.mutateAsync({
        name: values.name,
        version: values.version,
        kind: values.kind,
        backend: values.backend,
        artifactUri: values.artifactUri,
        seedTypeId: values.seedTypeId || undefined,
      });
      toast.success(t("models.registered", { name: model.name, version: model.version }));
      form.reset();
      setOpen(false);
    } catch (err) {
      applyApiError(err, form.setError);
    }
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button onClick={() => setOpen(true)}>
        <Plus className="h-4 w-4" /> {t("models.register")}
      </Button>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("models.register")}</DialogTitle>
          <DialogDescription>{t("models.registerDesc")}</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              id="name"
              label={t("field.name")}
              required
              error={form.formState.errors.name?.message}
            >
              <Input id="name" {...form.register("name")} />
            </Field>
            <Field
              id="version"
              label={t("field.version")}
              required
              error={form.formState.errors.version?.message}
            >
              <Input id="version" placeholder={t("models.versionPlaceholder")} {...form.register("version")} />
            </Field>
            <Field id="kind" label={t("field.kind")} required error={form.formState.errors.kind?.message}>
              <Select
                value={form.watch("kind")}
                onValueChange={(v) => form.setValue("kind", v as ModelKind)}
              >
                <SelectTrigger id="kind">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MODEL_KINDS.map((k) => (
                    <SelectItem key={k} value={k}>
                      {humanize(k)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field
              id="backend"
              label={t("field.backend")}
              required
              error={form.formState.errors.backend?.message}
            >
              <Select
                value={form.watch("backend")}
                onValueChange={(v) =>
                  form.setValue("backend", v as RegisterValues["backend"])
                }
              >
                <SelectTrigger id="backend">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MODEL_BACKENDS.map((b) => (
                    <SelectItem key={b} value={b}>
                      {humanize(b)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </div>
          <Field
            id="artifactUri"
            label={t("models.artifactUri")}
            required
            hint={t("models.artifactUriHint")}
            error={form.formState.errors.artifactUri?.message}
          >
            <Input id="artifactUri" {...form.register("artifactUri")} />
          </Field>
          <Field
            id="seedTypeId"
            label={t("field.seedType")}
            hint={t("models.seedTypeHint")}
            error={form.formState.errors.seedTypeId?.message}
          >
            <Controller
              control={form.control}
              name="seedTypeId"
              render={({ field }) => (
                <SeedTypeSelect
                  id="seedTypeId"
                  value={field.value ?? ""}
                  onChange={field.onChange}
                />
              )}
            />
          </Field>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={register.isPending}
            >
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={register.isPending}>
              {register.isPending ? <Spinner /> : null}
              {t("models.registerSubmit")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function ModelsPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const pagination = usePagination(20);
  const [kind, setKind] = useState<ModelKind | "">("");
  const [status, setStatus] = useState<ModelStatus | "">("");

  const query = useModels({
    page: pagination.page,
    pageSize: pagination.pageSize,
    kind: kind || undefined,
    status: status || undefined,
  });

  return (
    <>
      <PageHeader
        title={t("models.title")}
        description={t("models.description")}
        actions={<RegisterModelDialog />}
      />

      <div className="flex flex-wrap gap-3">
        <Select
          value={kind || ALL}
          onValueChange={(v) => {
            setKind(v === ALL ? "" : (v as ModelKind));
            pagination.setPage(1);
          }}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder={t("field.kind")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>{t("models.allKinds")}</SelectItem>
            {MODEL_KINDS.map((k) => (
              <SelectItem key={k} value={k}>
                {humanize(k)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={status || ALL}
          onValueChange={(v) => {
            setStatus(v === ALL ? "" : (v as ModelStatus));
            pagination.setPage(1);
          }}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder={t("field.status")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>{t("common.allStatuses")}</SelectItem>
            {MODEL_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {humanize(s)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : query.data.data.length === 0 ? (
        <EmptyState
          title={t("models.empty")}
          description={t("models.emptyDesc")}
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("field.name")}</TableHead>
                  <TableHead>{t("field.version")}</TableHead>
                  <TableHead>{t("field.kind")}</TableHead>
                  <TableHead>{t("field.backend")}</TableHead>
                  <TableHead>{t("field.status")}</TableHead>
                  <TableHead>{t("field.created")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {query.data.data.map((m) => (
                  <TableRow
                    key={m.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/models/${m.id}`)}
                  >
                    <TableCell className="font-medium">{m.name}</TableCell>
                    <TableCell className="font-mono text-xs">{m.version}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{humanize(m.kind)}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {humanize(m.backend)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={m.status} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDateTime(m.created_at)}
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
    </>
  );
}
