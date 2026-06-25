import { Boxes, CheckCircle2, ScanSearch, Sparkles } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { TranslationKey } from "@/i18n/dictionaries/en";
import { useI18n } from "@/i18n";

/**
 * Animated two-stage pipeline indicator shown while a batch is `pending` /
 * `running`. Mirrors the real backend pipeline (detection → quality
 * classification) so the wait reads as "the AI is working", not a dead spinner.
 * The page already polls every 2s; this is purely the visual stand-in until a
 * terminal status flips it to the results view.
 */
const STAGES: { icon: typeof ScanSearch; labelKey: TranslationKey; hintKey: TranslationKey }[] =
  [
    { icon: ScanSearch, labelKey: "analyzing.stage1", hintKey: "analyzing.stage1Hint" },
    { icon: Boxes, labelKey: "analyzing.stage2", hintKey: "analyzing.stage2Hint" },
  ];

export function AnalyzingIndicator({ pending }: { pending: boolean }) {
  const { t } = useI18n();
  return (
    <Card className="overflow-hidden">
      <CardContent className="space-y-5 p-6">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Sparkles className="h-4 w-4 animate-pulse text-primary" />
          {pending ? t("analyzing.queued") : t("analyzing.inProgress")}
          <span className="text-muted-foreground">{t("analyzing.updatesAuto")}</span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {STAGES.map((stage, i) => {
            const Icon = stage.icon;
            return (
              <div
                key={stage.labelKey}
                className="relative flex items-start gap-3 overflow-hidden rounded-lg border bg-card p-3"
              >
                {/* Sweeping shimmer to convey active work. */}
                <span
                  className="animate-shimmer pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-primary/10 to-transparent"
                  style={{ animationDelay: `${i * 0.4}s` }}
                />
                <span className="rounded-md bg-primary/10 p-2 text-primary">
                  <Icon className="h-4 w-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-medium">{t(stage.labelKey)}</p>
                  <p className="text-xs text-muted-foreground">{t(stage.hintKey)}</p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <CheckCircle2 className="h-3.5 w-3.5" />
          {t("analyzing.footer")}
        </div>
      </CardContent>
    </Card>
  );
}
