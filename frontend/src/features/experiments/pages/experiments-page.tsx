import { zodResolver } from "@hookform/resolvers/zod";
import { FlaskConical } from "lucide-react";
import { useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { Field } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { DatasetSelect, ModelSelect } from "@/components/shared/resource-select";
import { Pagination } from "@/components/shared/pagination";
import { StatusBadge } from "@/components/shared/status-badge";
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
import { EXPERIMENT_STATUSES } from "@/lib/api/types";
import type { ExperimentStatus } from "@/lib/api/types";
import { useI18n } from "@/i18n";
import { applyApiError } from "@/lib/form";
import { formatDateTime, formatDuration, humanize, shortId } from "@/lib/format";
import { usePagination } from "@/hooks/use-pagination";
import { useDatasets } from "@/features/datasets/api";
import { useModels } from "@/features/models/api";

import { useCreateExperiment, useExperiments } from "../api";

const ALL = "all";

interface FormValues {
  name: string;
  modelId: string;
  datasetId: string;
}

function RunExperimentDialog() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const create = useCreateExperiment();

  const schema = useMemo(
    () =>
      z.object({
        name: z.string().min(1, t("experiments.nameRequired")),
        modelId: z.string().uuid(t("experiments.selectModel")),
        datasetId: z.string().uuid(t("experiments.selectDataset")),
      }),
    [t],
  );

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", modelId: "", datasetId: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const experiment = await create.mutateAsync({
        name: values.name,
        model_id: values.modelId,
        dataset_id: values.datasetId,
      });
      toast.success(t("experiments.queued"));
      setOpen(false);
      form.reset();
      navigate(`/experiments/${experiment.id}`);
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
          <FlaskConical className="h-4 w-4" /> {t("experiments.run")}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>{t("experiments.run")}</DialogTitle>
            <DialogDescription>{t("experiments.runDesc")}</DialogDescription>
          </DialogHeader>

          <Field
            id="name"
            label={t("field.name")}
            required
            error={form.formState.errors.name?.message}
          >
            <Input id="name" {...form.register("name")} />
          </Field>
          <Field
            id="modelId"
            label={t("field.model")}
            required
            hint={t("experiments.modelHint")}
            error={form.formState.errors.modelId?.message}
          >
            <Controller
              control={form.control}
              name="modelId"
              render={({ field }) => (
                <ModelSelect id="modelId" value={field.value} onChange={field.onChange} />
              )}
            />
          </Field>
          <Field
            id="datasetId"
            label={t("field.dataset")}
            required
            hint={t("experiments.datasetHint")}
            error={form.formState.errors.datasetId?.message}
          >
            <Controller
              control={form.control}
              name="datasetId"
              render={({ field }) => (
                <DatasetSelect id="datasetId" value={field.value} onChange={field.onChange} />
              )}
            />
          </Field>

          <DialogFooter>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? <Spinner /> : null}
              {t("experiments.runSubmit")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function ExperimentsPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const pagination = usePagination(20);
  const [status, setStatus] = useState<ExperimentStatus | undefined>(undefined);
  const query = useExperiments({
    page: pagination.page,
    pageSize: pagination.pageSize,
    status,
  });
  const models = useModels({ page: 1, pageSize: 100 });
  const datasets = useDatasets({ page: 1, pageSize: 100 });
  const modelMap = new Map(
    (models.data?.data ?? []).map((m) => [m.id, `${m.name} ${m.version}`]),
  );
  const datasetMap = new Map((datasets.data?.data ?? []).map((d) => [d.id, d.name]));

  return (
    <>
      <PageHeader
        title={t("experiments.title")}
        description={t("experiments.description")}
        actions={<RunExperimentDialog />}
      />

      <div className="flex items-center gap-3">
        <Select
          value={status ?? ALL}
          onValueChange={(value) => {
            setStatus(value === ALL ? undefined : (value as ExperimentStatus));
            pagination.setPage(1);
          }}
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder={t("common.allStatuses")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>{t("common.allStatuses")}</SelectItem>
            {EXPERIMENT_STATUSES.map((s) => (
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
          title={t("experiments.empty")}
          description={t("experiments.emptyDesc")}
          action={<RunExperimentDialog />}
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("field.name")}</TableHead>
                  <TableHead>{t("field.status")}</TableHead>
                  <TableHead>{t("field.model")}</TableHead>
                  <TableHead>{t("field.dataset")}</TableHead>
                  <TableHead>{t("field.duration")}</TableHead>
                  <TableHead>{t("field.created")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {query.data.data.map((e) => (
                  <TableRow
                    key={e.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/experiments/${e.id}`)}
                  >
                    <TableCell className="font-medium">{e.name}</TableCell>
                    <TableCell>
                      <StatusBadge status={e.status} />
                    </TableCell>
                    <TableCell>
                      {modelMap.get(e.model_id) ??
                        t("experiments.modelFallback", { id: shortId(e.model_id) })}
                    </TableCell>
                    <TableCell>
                      {datasetMap.get(e.dataset_id) ??
                        t("experiments.datasetFallback", { id: shortId(e.dataset_id) })}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDuration(e.duration_ms)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDateTime(e.created_at)}
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
