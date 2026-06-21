import { zodResolver } from "@hookform/resolvers/zod";
import { Plus } from "lucide-react";
import { useState } from "react";
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
import { usePagination } from "@/hooks/use-pagination";
import { formatDateTime } from "@/lib/format";
import { applyApiError } from "@/lib/form";

import { useCreateDataset, useDatasets } from "../api";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional().or(z.literal("")),
});
type FormValues = z.infer<typeof schema>;

function CreateDatasetDialog() {
  const [open, setOpen] = useState(false);
  const create = useCreateDataset();
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
      toast.success("Dataset created.");
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
          <Plus className="h-4 w-4" /> Create dataset
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create dataset</DialogTitle>
          <DialogDescription>
            A dataset groups images and ground truth for offline evaluation.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <Field
            id="name"
            label="Name"
            required
            error={form.formState.errors.name?.message}
          >
            <Input id="name" placeholder="e.g. maize-holdout-2026" {...form.register("name")} />
          </Field>
          <Field
            id="description"
            label="Description"
            hint="Optional"
            error={form.formState.errors.description?.message}
          >
            <Input id="description" {...form.register("description")} />
          </Field>
          <DialogFooter>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? <Spinner /> : null}
              Create
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function DatasetsPage() {
  const navigate = useNavigate();
  const pagination = usePagination(20);
  const query = useDatasets({ page: pagination.page, pageSize: pagination.pageSize });

  return (
    <>
      <PageHeader
        title="Datasets"
        description="Frozen image sets with ground truth for model evaluation."
        actions={<CreateDatasetDialog />}
      />

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : query.data.data.length === 0 ? (
        <EmptyState
          title="No datasets yet"
          description="Create a dataset, then add image storage keys to evaluate models against it."
          action={<CreateDatasetDialog />}
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Items</TableHead>
                  <TableHead>Created</TableHead>
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
