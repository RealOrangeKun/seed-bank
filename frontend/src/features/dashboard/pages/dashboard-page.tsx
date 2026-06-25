import { Boxes, FlaskConical, Images, ScanLine } from "lucide-react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { LoadingState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useBatches } from "@/features/batches/api";
import { hasRole, useAuth } from "@/features/auth/use-auth";
import { useI18n } from "@/i18n";
import { formatDateTime } from "@/lib/format";

import { StatsStrip } from "../components/stats-strip";

function QuickAction({
  to,
  icon: Icon,
  title,
  description,
}: {
  to: string;
  icon: typeof ScanLine;
  title: string;
  description: string;
}) {
  return (
    <Link to={to}>
      <Card className="h-full transition-colors hover:border-primary/60">
        <CardContent className="flex items-start gap-3 p-5">
          <span className="rounded-md bg-primary/10 p-2 text-primary">
            <Icon className="h-5 w-5" />
          </span>
          <div className="space-y-0.5">
            <p className="font-medium">{title}</p>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const { t, tn } = useI18n();
  const isDeveloper = hasRole(user, ["ai_developer", "admin"]);
  // One fetch backs both the stats strip (whole window) and the recent list
  // (first five), so the dashboard makes a single batches request.
  const recent = useBatches({ page: 1, pageSize: 50 });
  const recentFive = (recent.data?.data ?? []).slice(0, 5);

  const firstName = user?.full_name ? user.full_name.split(" ")[0] : "";

  return (
    <>
      <PageHeader
        title={
          firstName ? t("dashboard.welcomeNamed", { name: firstName }) : t("dashboard.welcome")
        }
        description={t("dashboard.subtitle")}
        actions={
          <Button asChild>
            <Link to="/analyze">
              <ScanLine className="h-4 w-4" /> {t("dashboard.quickAnalyzeTitle")}
            </Link>
          </Button>
        }
      />

      {recent.data && recent.data.data.length > 0 ? (
        <StatsStrip batches={recent.data.data} />
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickAction
          to="/analyze"
          icon={ScanLine}
          title={t("dashboard.quickAnalyzeTitle")}
          description={t("dashboard.quickAnalyzeDesc")}
        />
        <QuickAction
          to="/batches"
          icon={Images}
          title={t("dashboard.quickBatchesTitle")}
          description={t("dashboard.quickBatchesDesc")}
        />
        {isDeveloper ? (
          <>
            <QuickAction
              to="/models"
              icon={Boxes}
              title={t("dashboard.quickModelsTitle")}
              description={t("dashboard.quickModelsDesc")}
            />
            <QuickAction
              to="/experiments"
              icon={FlaskConical}
              title={t("dashboard.quickExperimentsTitle")}
              description={t("dashboard.quickExperimentsDesc")}
            />
          </>
        ) : null}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("dashboard.recentScans")}</CardTitle>
        </CardHeader>
        <CardContent>
          {recent.isPending ? (
            <LoadingState />
          ) : recent.isError || recentFive.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              {t("dashboard.noScans")}
            </p>
          ) : (
            <ul className="divide-y">
              {recentFive.map((b) => (
                <li key={b.id}>
                  <Link
                    to={`/batches/${b.id}`}
                    className="flex items-center justify-between gap-3 py-3 text-sm hover:text-primary"
                  >
                    <span className="font-medium">{formatDateTime(b.submitted_at)}</span>
                    <StatusBadge status={b.status} />
                    <span className="text-muted-foreground">
                      {tn("images", b.image_count)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </>
  );
}
