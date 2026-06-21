import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Save, Trash2 } from "lucide-react";
import { useState } from "react";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { CopyButton } from "@/components/shared/copy-button";
import { Field } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { ModelSelect, SeedTypeSelect } from "@/components/shared/resource-select";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ModelKind } from "@/lib/api/types";
import { MODEL_KINDS } from "@/lib/api/types";
import { formatDateTime, humanize, shortId } from "@/lib/format";
import { applyApiError } from "@/lib/form";

import { useReplaceTrafficSplits, useTrafficSplits, type TrafficSegment } from "../api";

const entrySchema = z.object({
  model_id: z.string().uuid("Select a model"),
  weight: z.coerce
    .number({ invalid_type_error: "Weight is required" })
    .int("Whole number")
    .min(0, "0–100")
    .max(100, "0–100"),
});

const schema = z
  .object({
    entries: z.array(entrySchema).max(16, "At most 16 entries"),
  })
  .refine(
    (v) => v.entries.reduce((sum, e) => sum + (Number.isFinite(e.weight) ? e.weight : 0), 0) <= 100,
    { message: "Weights must sum to 100 or less", path: ["entries"] },
  );

type FormValues = z.infer<typeof schema>;

export function TrafficPage() {
  // The loaded segment drives the GET; the selector below stages the next one.
  const [kind, setKind] = useState<ModelKind>("detection");
  const [seedTypeId, setSeedTypeId] = useState("");
  const [segment, setSegment] = useState<TrafficSegment | null>(null);

  const splits = useTrafficSplits(segment ?? { kind: "detection" }, segment !== null);
  const replace = useReplaceTrafficSplits();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { entries: [{ model_id: "", weight: 100 }] },
  });
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "entries",
  });

  const entries = form.watch("entries");
  const total = entries.reduce((sum, e) => {
    const n = Number(e.weight);
    return sum + (Number.isFinite(n) ? n : 0);
  }, 0);

  function loadSegment() {
    setSegment({ kind, seedTypeId: seedTypeId.trim() || undefined });
  }

  const onSubmit = form.handleSubmit(async (values) => {
    if (!segment) {
      toast.error("Load a segment first.");
      return;
    }
    try {
      await replace.mutateAsync({
        kind: segment.kind,
        seedTypeId: segment.seedTypeId,
        entries: values.entries.map((e) => ({ model_id: e.model_id, weight: e.weight })),
      });
      toast.success("Traffic split updated.");
    } catch (err) {
      applyApiError(err, form.setError);
    }
  });

  const rootError = form.formState.errors.entries?.root?.message ?? form.formState.errors.entries?.message;

  return (
    <>
      <PageHeader
        title="Traffic splits"
        description="Route inference traffic across model versions per segment."
      />

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Segment</CardTitle>
            <CardDescription>
              Choose the model kind and an optional seed type, then load its current splits.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <Field id="segment-kind" label="Kind" className="sm:w-48">
                <Select value={kind} onValueChange={(v) => setKind(v as ModelKind)}>
                  <SelectTrigger id="segment-kind">
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
                id="segment-seed-type"
                label="Seed type"
                hint="Leave as default to route all seed types"
                className="flex-1"
              >
                <SeedTypeSelect
                  id="segment-seed-type"
                  value={seedTypeId}
                  onChange={setSeedTypeId}
                  includeNone
                />
              </Field>
              <Button type="button" onClick={loadSegment}>
                Load
              </Button>
            </div>
          </CardContent>
        </Card>

        {segment ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Current splits · {humanize(segment.kind)}
                {segment.seedTypeId ? ` · ${shortId(segment.seedTypeId)}` : " · default"}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {splits.isPending ? (
                <LoadingState />
              ) : splits.isError ? (
                <ErrorState error={splits.error} />
              ) : (splits.data ?? []).length === 0 ? (
                <EmptyState
                  title="No active splits"
                  description="This segment has no traffic splits configured yet."
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Model</TableHead>
                      <TableHead>Weight</TableHead>
                      <TableHead>State</TableHead>
                      <TableHead>Valid from</TableHead>
                      <TableHead>Valid until</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(splits.data ?? []).map((s) => (
                      <TableRow key={s.id}>
                        <TableCell>
                          <span className="inline-flex items-center gap-1 font-mono text-xs">
                            {shortId(s.model_id)}
                            <CopyButton value={s.model_id} label="Copy model id" />
                          </span>
                        </TableCell>
                        <TableCell>{s.weight}</TableCell>
                        <TableCell>
                          <StatusBadge status={s.is_active ? "active" : "archived"} />
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {s.valid_from ? formatDateTime(s.valid_from) : "—"}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {s.valid_until ? formatDateTime(s.valid_until) : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Edit split</CardTitle>
            <CardDescription>
              Replace the active splits for the loaded segment. Weights must sum to 100 or less.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-4" noValidate>
              <div className="space-y-3">
                {fields.map((field, index) => (
                  <div key={field.id} className="flex items-start gap-3">
                    <Field
                      id={`entries.${index}.model_id`}
                      label="Model"
                      className="flex-1"
                      error={form.formState.errors.entries?.[index]?.model_id?.message}
                    >
                      <Controller
                        control={form.control}
                        name={`entries.${index}.model_id`}
                        render={({ field: f }) => (
                          <ModelSelect
                            id={`entries.${index}.model_id`}
                            value={f.value}
                            onChange={f.onChange}
                            kind={segment?.kind ?? kind}
                          />
                        )}
                      />
                    </Field>
                    <Field
                      id={`entries.${index}.weight`}
                      label="Weight"
                      className="w-28"
                      error={form.formState.errors.entries?.[index]?.weight?.message}
                    >
                      <Input
                        id={`entries.${index}.weight`}
                        type="number"
                        min={0}
                        max={100}
                        {...form.register(`entries.${index}.weight`)}
                      />
                    </Field>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="mt-7"
                      aria-label="Remove entry"
                      disabled={fields.length <= 1}
                      onClick={() => remove(index)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={fields.length >= 16}
                  onClick={() => append({ model_id: "", weight: 0 })}
                >
                  <Plus className="h-4 w-4" /> Add model
                </Button>
                <span
                  className={`text-sm font-medium ${total > 100 ? "text-destructive" : "text-muted-foreground"}`}
                >
                  Total weight: {total} / 100
                </span>
              </div>

              {rootError ? (
                <p className="text-xs text-destructive" role="alert">
                  {rootError}
                </p>
              ) : null}

              <div className="flex justify-end">
                <Button type="submit" disabled={replace.isPending || !segment}>
                  <Save className="h-4 w-4" />
                  Save split
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
