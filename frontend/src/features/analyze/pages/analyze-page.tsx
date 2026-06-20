import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronDown, Sparkles } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { Field } from "@/components/shared/field";
import { FileDropzone } from "@/components/shared/file-dropzone";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { hasRole, useAuth } from "@/features/auth/use-auth";
import { applyApiError } from "@/lib/form";

import { useAnalyze } from "../api";

const uuid = z.string().uuid("Must be a valid UUID").optional().or(z.literal(""));
const schema = z.object({
  supplierId: uuid,
  seedTypeId: uuid,
  modelId: uuid,
  countryCode: z
    .string()
    .regex(/^[A-Z]{2}$/, "Two uppercase letters, e.g. KE")
    .optional()
    .or(z.literal("")),
  gpsLat: z.string().optional().or(z.literal("")),
  gpsLong: z.string().optional().or(z.literal("")),
});
type FormValues = z.infer<typeof schema>;

export function AnalyzePage() {
  const { user } = useAuth();
  const canOverrideModel = hasRole(user, ["ai_developer", "admin"]);
  const navigate = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const analyze = useAnalyze();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      supplierId: "",
      seedTypeId: "",
      modelId: "",
      countryCode: "",
      gpsLat: "",
      gpsLong: "",
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    if (files.length === 0) {
      toast.error("Add at least one image.");
      return;
    }
    try {
      const batch = await analyze.mutateAsync({
        files,
        supplierId: values.supplierId || undefined,
        seedTypeId: values.seedTypeId || undefined,
        modelId: canOverrideModel ? values.modelId || undefined : undefined,
        countryCode: values.countryCode || undefined,
        gpsLat: values.gpsLat || undefined,
        gpsLong: values.gpsLong || undefined,
      });
      toast.success("Analysis started.");
      navigate(`/batches/${batch.id}`);
    } catch (err) {
      applyApiError(err, form.setError);
    }
  });

  return (
    <>
      <PageHeader
        title="New analysis"
        description="Upload seed images to run detection and quality classification."
      />

      <form onSubmit={onSubmit} className="space-y-6">
        <Card>
          <CardContent className="p-5">
            <FileDropzone
              files={files}
              onChange={setFiles}
              disabled={analyze.isPending}
            />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4 p-5">
            <button
              type="button"
              onClick={() => setShowAdvanced((s) => !s)}
              className="flex w-full items-center justify-between text-sm font-medium"
            >
              Optional metadata
              <ChevronDown
                className={`h-4 w-4 transition-transform ${showAdvanced ? "rotate-180" : ""}`}
              />
            </button>

            {showAdvanced ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <Field
                  id="seedTypeId"
                  label="Seed type ID"
                  hint="Optional UUID; targets a specific seed type"
                  error={form.formState.errors.seedTypeId?.message}
                >
                  <Input id="seedTypeId" {...form.register("seedTypeId")} />
                </Field>
                <Field
                  id="supplierId"
                  label="Supplier ID"
                  hint="Optional UUID"
                  error={form.formState.errors.supplierId?.message}
                >
                  <Input id="supplierId" {...form.register("supplierId")} />
                </Field>
                <Field
                  id="countryCode"
                  label="Country code"
                  hint="ISO-2, e.g. KE"
                  error={form.formState.errors.countryCode?.message}
                >
                  <Input id="countryCode" maxLength={2} {...form.register("countryCode")} />
                </Field>
                <div className="grid grid-cols-2 gap-2">
                  <Field
                    id="gpsLat"
                    label="GPS lat"
                    error={form.formState.errors.gpsLat?.message}
                  >
                    <Input id="gpsLat" {...form.register("gpsLat")} />
                  </Field>
                  <Field
                    id="gpsLong"
                    label="GPS long"
                    error={form.formState.errors.gpsLong?.message}
                  >
                    <Input id="gpsLong" {...form.register("gpsLong")} />
                  </Field>
                </div>
                {canOverrideModel ? (
                  <Field
                    id="modelId"
                    label="Model override"
                    hint="Developer-only: force a specific model UUID"
                    error={form.formState.errors.modelId?.message}
                    className="sm:col-span-2"
                  >
                    <Input id="modelId" {...form.register("modelId")} />
                  </Field>
                ) : null}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" size="lg" disabled={analyze.isPending}>
            {analyze.isPending ? <Spinner /> : <Sparkles className="h-4 w-4" />}
            Analyze {files.length > 0 ? `${files.length} image${files.length > 1 ? "s" : ""}` : ""}
          </Button>
        </div>
      </form>
    </>
  );
}
