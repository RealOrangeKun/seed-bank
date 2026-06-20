import { zodResolver } from "@hookform/resolvers/zod";
import { FlaskConical } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { Field } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
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
import { applyApiError } from "@/lib/form";
import { formatDateTime, formatDuration, humanize, shortId } from "@/lib/format";
import { usePagination } from "@/hooks/use-pagination";

import { useCreateExperiment, useExperiments } from "../api";

const ALL = "all";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  modelId: z.string().uuid("Must be a valid UUID"),
  datasetId: z.string().uuid("Must be a valid UUID"),
});
type FormValues = z.infer<typeof schema>;

function RunExperimentDialog() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const create = useCreateExperiment();

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
      toast.success("Experiment queued.");
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
          <FlaskConical className="h-4 w-4" /> Run experiment
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Run experiment</DialogTitle>
            <DialogDescription>
              Evaluate a model against a frozen dataset.
            </DialogDescription>
          </DialogHeader>

          <Field
            id="name"
            label="Name"
            required
            error={form.formState.errors.name?.message}
          >
            <Input id="name" {...form.register("name")} />
          </Field>
          <Field
            id="modelId"
            label="Model ID"
            required
            hint="UUID of the model to evaluate"
            error={form.formState.errors.modelId?.message}
          >
            <Input id="modelId" {...form.register("modelId")} />
          </Field>
          <Field
            id="datasetId"
            label="Dataset ID"
            required
            hint="UUID of the frozen dataset"
            error={form.formState.errors.datasetId?.message}
          >
            <Input id="datasetId" {...form.register("datasetId")} />
          </Field>

          <DialogFooter>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? <Spinner /> : null}
              Run
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function ExperimentsPage() {
  const navigate = useNavigate();
  const pagination = usePagination(20);
  const [status, setStatus] = useState<ExperimentStatus | undefined>(undefined);
  const query = useExperiments({
    page: pagination.page,
    pageSize: pagination.pageSize,
    status,
  });

  return (
    <>
      <PageHeader
        title="Experiments"
        description="Offline evaluations of models against frozen datasets."
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
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
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
          title="No experiments yet"
          description="Run an evaluation to compare a model against a dataset."
          action={<RunExperimentDialog />}
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Dataset</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Created</TableHead>
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
                    <TableCell className="font-mono text-xs">
                      {shortId(e.model_id)}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {shortId(e.dataset_id)}
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
