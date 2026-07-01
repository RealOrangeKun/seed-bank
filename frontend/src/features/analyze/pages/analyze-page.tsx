import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronDown, Film, ImageIcon, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { Field } from "@/components/shared/field";
import { FileDropzone } from "@/components/shared/file-dropzone";
import { PageHeader } from "@/components/shared/page-header";
import { VideoDropzone } from "@/components/shared/video-dropzone";
import {
  ModelSelect,
  SeedTypeSelect,
  SupplierSelect,
} from "@/components/shared/resource-select";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { hasRole, useAuth } from "@/features/auth/use-auth";
import { useI18n } from "@/i18n";
import { applyApiError } from "@/lib/form";

import { type AnalyzeMode, useAnalyze } from "../api";

interface FormValues {
  mode: AnalyzeMode;
  supplierId?: string;
  seedTypeId?: string;
  modelId?: string;
  countryCode?: string;
  gpsLat?: string;
  gpsLong?: string;
}

export function AnalyzePage() {
  const { user } = useAuth();
  const { t, tn } = useI18n();
  const canOverrideModel = hasRole(user, ["ai_developer", "admin"]);
  const navigate = useNavigate();
  const [tab, setTab] = useState<"images" | "video">("images");
  const [files, setFiles] = useState<File[]>([]);
  const [video, setVideo] = useState<File | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const analyze = useAnalyze();

  const schema = useMemo(() => {
    const uuid = z.string().uuid(t("analyze.errUuid")).optional().or(z.literal(""));
    return z.object({
      mode: z.enum(["fast", "accurate"]),
      supplierId: uuid,
      seedTypeId: uuid,
      modelId: uuid,
      countryCode: z
        .string()
        .regex(/^[A-Z]{2}$/, t("analyze.errCountryCode"))
        .optional()
        .or(z.literal("")),
      gpsLat: z.string().optional().or(z.literal("")),
      gpsLong: z.string().optional().or(z.literal("")),
    });
  }, [t]);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      mode: "accurate",
      supplierId: "",
      seedTypeId: "",
      modelId: "",
      countryCode: "",
      gpsLat: "",
      gpsLong: "",
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    const isVideo = tab === "video";
    if (isVideo && !video) {
      toast.error(t("analyze.needVideo"));
      return;
    }
    if (!isVideo && files.length === 0) {
      toast.error(t("analyze.needImage"));
      return;
    }
    try {
      const batch = await analyze.mutateAsync(
        isVideo
          ? {
              // Video is always YOLO-only on the server; mode / seed type /
              // model override are ignored, so we don't send them.
              files: [video as File],
              supplierId: values.supplierId || undefined,
              countryCode: values.countryCode || undefined,
              gpsLat: values.gpsLat || undefined,
              gpsLong: values.gpsLong || undefined,
            }
          : {
              files,
              // An explicit model override (admin) wins; otherwise fast/accurate.
              mode: canOverrideModel && values.modelId ? undefined : values.mode,
              supplierId: values.supplierId || undefined,
              seedTypeId: values.seedTypeId || undefined,
              modelId: canOverrideModel ? values.modelId || undefined : undefined,
              countryCode: values.countryCode || undefined,
              gpsLat: values.gpsLat || undefined,
              gpsLong: values.gpsLong || undefined,
            },
      );
      toast.success(t("analyze.started"));
      navigate(`/batches/${batch.id}`);
    } catch (err) {
      applyApiError(err, form.setError);
    }
  });

  return (
    <>
      <PageHeader title={t("analyze.title")} description={t("analyze.description")} />

      <form onSubmit={onSubmit} className="space-y-6">
        <div
          role="tablist"
          aria-label={t("analyze.title")}
          className="inline-flex rounded-lg border bg-muted/40 p-1"
        >
          {[
            { value: "images" as const, label: t("analyze.tabImages"), Icon: ImageIcon },
            { value: "video" as const, label: t("analyze.tabVideo"), Icon: Film },
          ].map(({ value, label, Icon }) => {
            const active = tab === value;
            return (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setTab(value)}
                className={`inline-flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            );
          })}
        </div>

        <Card>
          <CardContent className="p-5">
            {tab === "images" ? (
              <FileDropzone
                files={files}
                onChange={setFiles}
                disabled={analyze.isPending}
              />
            ) : (
              <VideoDropzone
                file={video}
                onChange={setVideo}
                disabled={analyze.isPending}
              />
            )}
          </CardContent>
        </Card>

        {tab === "video" ? (
          <Card>
            <CardContent className="flex items-start gap-3 p-5 text-sm text-muted-foreground">
              <Film className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <p>{t("analyze.videoNote")}</p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="p-5">
              <Controller
                control={form.control}
                name="mode"
                render={({ field }) => (
                  <div className="space-y-3">
                    <p className="text-sm font-medium">{t("analyze.mode")}</p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {[
                        {
                          value: "fast" as const,
                          title: t("analyze.modeFast"),
                          hint: t("analyze.modeFastHint"),
                        },
                        {
                          value: "accurate" as const,
                          title: t("analyze.modeAccurate"),
                          hint: t("analyze.modeAccurateHint"),
                        },
                      ].map((opt) => {
                        const active = field.value === opt.value;
                        return (
                          <button
                            key={opt.value}
                            type="button"
                            aria-pressed={active}
                            onClick={() => field.onChange(opt.value)}
                            className={`rounded-lg border p-4 text-left transition-colors ${
                              active
                                ? "border-primary bg-primary/5 ring-1 ring-primary"
                                : "border-border hover:bg-muted/50"
                            }`}
                          >
                            <span className="block text-sm font-semibold">
                              {opt.title}
                            </span>
                            <span className="mt-1 block text-xs text-muted-foreground">
                              {opt.hint}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              />
            </CardContent>
          </Card>
        )}

        <Card>
          <CardContent className="space-y-4 p-5">
            <button
              type="button"
              onClick={() => setShowAdvanced((s) => !s)}
              className="flex w-full items-center justify-between text-sm font-medium"
            >
              {t("analyze.optionalMetadata")}
              <ChevronDown
                className={`h-4 w-4 transition-transform ${showAdvanced ? "rotate-180" : ""}`}
              />
            </button>

            {showAdvanced ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {tab !== "video" ? (
                  <Field
                    id="seedTypeId"
                    label={t("analyze.seedType")}
                    hint={t("analyze.seedTypeHint")}
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
                ) : null}
                <Field
                  id="supplierId"
                  label={t("analyze.supplier")}
                  hint={t("analyze.supplierHint")}
                  error={form.formState.errors.supplierId?.message}
                >
                  <Controller
                    control={form.control}
                    name="supplierId"
                    render={({ field }) => (
                      <SupplierSelect
                        id="supplierId"
                        value={field.value ?? ""}
                        onChange={field.onChange}
                      />
                    )}
                  />
                </Field>
                <Field
                  id="countryCode"
                  label={t("analyze.countryCode")}
                  hint={t("analyze.countryCodeHint")}
                  error={form.formState.errors.countryCode?.message}
                >
                  <Input
                    id="countryCode"
                    maxLength={2}
                    {...form.register("countryCode")}
                  />
                </Field>
                <div className="grid grid-cols-2 gap-2">
                  <Field
                    id="gpsLat"
                    label={t("analyze.gpsLat")}
                    error={form.formState.errors.gpsLat?.message}
                  >
                    <Input id="gpsLat" {...form.register("gpsLat")} />
                  </Field>
                  <Field
                    id="gpsLong"
                    label={t("analyze.gpsLong")}
                    error={form.formState.errors.gpsLong?.message}
                  >
                    <Input id="gpsLong" {...form.register("gpsLong")} />
                  </Field>
                </div>
                {canOverrideModel && tab !== "video" ? (
                  <Field
                    id="modelId"
                    label={t("analyze.modelOverride")}
                    hint={t("analyze.modelOverrideHint")}
                    error={form.formState.errors.modelId?.message}
                    className="sm:col-span-2"
                  >
                    <Controller
                      control={form.control}
                      name="modelId"
                      render={({ field }) => (
                        <ModelSelect
                          id="modelId"
                          value={field.value ?? ""}
                          onChange={field.onChange}
                          includeNone
                        />
                      )}
                    />
                  </Field>
                ) : null}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" size="lg" disabled={analyze.isPending}>
            {analyze.isPending ? <Spinner /> : <Sparkles className="h-4 w-4" />}
            {tab === "video"
              ? t("analyze.submitVideo")
              : files.length > 0
                ? `${t("analyze.submit")} · ${tn("images", files.length)}`
                : t("analyze.submit")}
          </Button>
        </div>
      </form>
    </>
  );
}
