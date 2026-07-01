/**
 * Client-side PDF report for a scan batch — the end-user-facing alternative to
 * the developer CSV/JSON export. Lists each image's good/bad verdict (good-seed
 * share vs. the configured threshold) plus the batch's overall verdict, built
 * entirely in the browser with jsPDF so there's no backend/PDF dependency.
 *
 * Text/table only by design: embedding image thumbnails would require reading
 * cross-origin MinIO bytes onto a canvas (CORS-tainted). Images are identified
 * by order ("Image 1", "Image 2", …), matching the on-screen card order.
 */
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";

import type { I18nContextValue } from "@/i18n";
import { formatDateTime, shortId } from "@/lib/format";
import type { BatchDetailOut } from "@/lib/api/types";

import { computeImageInsights, computeInsights, verdictFor, type ImageVerdict } from "./insights";

type T = I18nContextValue["t"];

const PASS_GREEN: [number, number, number] = [34, 160, 90];
const FAIL_RED: [number, number, number] = [200, 50, 50];

function pct(rate: number | null): string {
  return rate === null ? "—" : `${Math.round(rate * 100)}%`;
}

function verdictLabel(verdict: ImageVerdict, t: T): string {
  if (verdict === "good") return t("detail.verdictGood");
  if (verdict === "bad") return t("detail.verdictBad");
  return t("detail.verdictNone");
}

/** Build and download a per-image good/bad PDF report for a batch. */
export function generateBatchReportPdf(
  batch: BatchDetailOut,
  threshold: number,
  t: T,
): void {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const insights = computeInsights(batch);
  const overallClassified = insights.good + insights.bad;
  const overallRate = overallClassified > 0 ? insights.good / overallClassified : null;
  const overallVerdict = verdictFor(overallRate, threshold);

  // ── Header ────────────────────────────────────────────────────────────────
  doc.setFontSize(18);
  doc.text(t("report.title"), 14, 18);

  doc.setFontSize(10);
  doc.setTextColor(110);
  doc.text(t("report.generated", { date: formatDateTime(batch.submitted_at) }), 14, 26);
  doc.text(t("report.threshold", { pct: Math.round(threshold * 100) }), 14, 31);

  doc.setFontSize(12);
  const overallColor: [number, number, number] =
    overallVerdict === null
      ? [110, 110, 110]
      : overallVerdict === "bad"
        ? FAIL_RED
        : PASS_GREEN;
  doc.setTextColor(overallColor[0], overallColor[1], overallColor[2]);
  doc.text(
    t("report.overall", {
      verdict: verdictLabel(overallVerdict, t),
      pct: pct(overallRate),
    }),
    14,
    40,
  );
  doc.setTextColor(0);

  // ── Per-image table ─────────────────────────────────────────────────────────
  const verdicts: ImageVerdict[] = [];
  const body = (batch.images ?? []).map((image, i) => {
    const s = computeImageInsights(image);
    const v = verdictFor(s.goodRate, threshold);
    verdicts.push(v);
    return [
      t("report.imageN", { n: i + 1 }),
      String(s.total),
      String(s.good),
      String(s.bad),
      String(s.unclassified),
      pct(s.goodRate),
      verdictLabel(v, t),
    ];
  });

  autoTable(doc, {
    startY: 46,
    head: [
      [
        t("report.colImage"),
        t("report.colDetections"),
        t("report.colGood"),
        t("report.colBad"),
        t("report.colUnclassified"),
        t("report.colGoodRate"),
        t("report.colVerdict"),
      ],
    ],
    body,
    styles: { fontSize: 9, cellPadding: 2 },
    headStyles: { fillColor: [34, 100, 64] },
    // Tint the verdict cell (last column) green/red so the report scans fast.
    didParseCell: (data) => {
      if (data.section === "body" && data.column.index === 6) {
        const v = verdicts[data.row.index];
        if (v === "good") data.cell.styles.textColor = PASS_GREEN;
        else if (v === "bad") data.cell.styles.textColor = FAIL_RED;
      }
    },
  });

  doc.save(`scan-report-${shortId(batch.id)}.pdf`);
}
