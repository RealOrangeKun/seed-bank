import { zodResolver } from "@hookform/resolvers/zod";
import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { Field } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/shared/pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import { formatDateTime } from "@/lib/format";
import { applyApiError } from "@/lib/form";

import { useCreateDataset, useDatasets } from "../api";

interface FormValues {
  name: string;
  description?: string;
}

function CreateDatasetDialog() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const create = useCreateDataset();
  const schema = useMemo(
    () =>
      z.object({
        name: z.string().min(1, t("datasets.nameRequired")),
        description: z.string().optional().or(z.literal("")),
      }),
    [t],
  );
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", description: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await create.mutateAsync({
        name: values.name,
        description: values.description || undefined,
      });
      toast.success(t("datasets.created"));
      form.reset();
      setOpen(false);
    } catch (err) {
      applyApiError(err, form.setError);
    }
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) form.reset();
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4" /> {t("datasets.create")}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("datasets.create")}</DialogTitle>
          <DialogDescription>{t("datasets.createDesc")}</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <Field
            id="name"
            label={t("field.name")}
            required
            error={form.formState.errors.name?.message}
          >
            <Input id="name" placeholder={t("datasets.namePlaceholder")} {...form.register("name")} />
          </Field>
          <Field
            id="description"
            label={t("field.description")}
            hint={t("common.optional")}
            error={form.formState.errors.description?.message}
          >
            <Input id="description" {...form.register("description")} />
          </Field>
          <DialogFooter>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? <Spinner /> : null}
              {t("common.create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function DatasetsPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const pagination = usePagination(20);
  const query = useDatasets({ page: pagination.page, pageSize: pagination.pageSize });

  return (
    <>
      <PageHeader
        title={t("datasets.title")}
        description={t("datasets.description")}
        actions={<CreateDatasetDialog />}
      />

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : query.data.data.length === 0 ? (
        <EmptyState
          title={t("datasets.empty")}
          description={t("datasets.emptyDesc")}
          action={<CreateDatasetDialog />}
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("field.name")}</TableHead>
                  <TableHead>{t("field.description")}</TableHead>
                  <TableHead>{t("field.items")}</TableHead>
                  <TableHead>{t("field.created")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {query.data.data.map((d) => (
                  <TableRow
                    key={d.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/datasets/${d.id}`)}
                  >
                    <TableCell className="font-medium">{d.name}</TableCell>
                    <TableCell className="max-w-md truncate text-muted-foreground">
                      {d.description ?? "—"}
                    </TableCell>
                    <TableCell className="tabular-nums">{d.item_count}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDateTime(d.created_at)}
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
