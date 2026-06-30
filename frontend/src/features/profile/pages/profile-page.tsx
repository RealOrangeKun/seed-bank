import { CopyButton } from "@/components/shared/copy-button";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/features/auth/use-auth";
import { useI18n } from "@/i18n";
import { formatDateTime } from "@/lib/format";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

export function ProfilePage() {
  const { user } = useAuth();
  const { t } = useI18n();
  if (!user) return null;

  return (
    <>
      <PageHeader title={t("profile.title")} description={t("profile.description")} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("profile.account")}</CardTitle>
          </CardHeader>
          <CardContent className="divide-y">
            <Row
              label={t("profile.email")}
              value={
                <span className="inline-flex items-center gap-1">
                  {user.email}
                  {user.is_verified ? (
                    <Badge variant="success">{t("profile.verified")}</Badge>
                  ) : (
                    <Badge variant="warning">{t("profile.unverified")}</Badge>
                  )}
                </span>
              }
            />
            <Row label={t("profile.fullName")} value={user.full_name || "—"} />
            <Row label={t("profile.role")} value={<StatusBadge status={user.role} />} />
            <Row
              label={t("profile.status")}
              value={<StatusBadge status={user.is_active ? "active" : "archived"} />}
            />
            <Row
              label={t("profile.lastLogin")}
              value={formatDateTime(user.last_login_at) || "—"}
            />
            <Row
              label={t("profile.userId")}
              value={
                <span className="inline-flex items-center gap-1 font-mono text-xs">
                  {user.id}
                  <CopyButton value={user.id} label={t("profile.copyUserId")} />
                </span>
              }
            />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
