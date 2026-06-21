import { Boxes, FlaskConical, Images, ScanLine } from "lucide-react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { LoadingState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useBatches } from "@/features/batches/api";
import { hasRole, useAuth } from "@/features/auth/use-auth";
import { formatDateTime } from "@/lib/format";

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
  const isDeveloper = hasRole(user, ["ai_developer", "admin"]);
  const recent = useBatches({ page: 1, pageSize: 5 });

  return (
    <>
      <PageHeader
        title={`Welcome${user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}`}
        description="Analyze seeds and review recent activity."
        actions={
          <Button asChild>
            <Link to="/analyze">
              <ScanLine className="h-4 w-4" /> New analysis
            </Link>
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <QuickAction
          to="/analyze"
          icon={ScanLine}
          title="Analyze seeds"
          description="Upload images for detection & grading"
        />
        <QuickAction
          to="/batches"
          icon={Images}
          title="Scan history"
          description="Review your past analyses"
        />
        {isDeveloper ? (
          <>
            <QuickAction
              to="/models"
              icon={Boxes}
              title="Models"
              description="Register, promote, compare"
            />
            <QuickAction
              to="/experiments"
              icon={FlaskConical}
              title="Experiments"
              description="Offline evaluation runs"
            />
          </>
        ) : null}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent scans</CardTitle>
        </CardHeader>
        <CardContent>
          {recent.isPending ? (
            <LoadingState />
          ) : recent.isError || recent.data.data.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No scans yet. Start with a new analysis.
            </p>
          ) : (
            <ul className="divide-y">
              {recent.data.data.map((b) => (
                <li key={b.id}>
                  <Link
                    to={`/batches/${b.id}`}
                    className="flex items-center justify-between gap-3 py-3 text-sm hover:text-primary"
                  >
                    <span className="font-medium">{formatDateTime(b.submitted_at)}</span>
                    <StatusBadge status={b.status} />
                    <span className="text-muted-foreground">
                      {b.image_count} image{b.image_count === 1 ? "" : "s"}
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
