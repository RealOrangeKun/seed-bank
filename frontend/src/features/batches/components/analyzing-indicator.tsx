import { Boxes, CheckCircle2, ScanSearch, Sparkles } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

/**
 * Animated two-stage pipeline indicator shown while a batch is `pending` /
 * `running`. Mirrors the real backend pipeline (detection → quality
 * classification) so the wait reads as "the AI is working", not a dead spinner.
 * The page already polls every 2s; this is purely the visual stand-in until a
 * terminal status flips it to the results view.
 */
const STAGES = [
  { icon: ScanSearch, label: "Detecting seeds", hint: "Locating each seed in the image" },
  { icon: Boxes, label: "Grading quality", hint: "Classifying good vs. bad per seed" },
] as const;

export function AnalyzingIndicator({ pending }: { pending: boolean }) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="space-y-5 p-6">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Sparkles className="h-4 w-4 animate-pulse text-primary" />
          {pending ? "Queued for analysis…" : "Analysis in progress"}
          <span className="text-muted-foreground">· updates automatically</span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {STAGES.map((stage, i) => {
            const Icon = stage.icon;
            return (
              <div
                key={stage.label}
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
                  <p className="text-sm font-medium">{stage.label}</p>
                  <p className="text-xs text-muted-foreground">{stage.hint}</p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Results and bounding boxes appear here the moment they're ready.
        </div>
      </CardContent>
    </Card>
  );
}
