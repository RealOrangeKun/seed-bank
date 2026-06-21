import { KeyRound } from "lucide-react";
import { Link } from "react-router-dom";

import { CopyButton } from "@/components/shared/copy-button";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/features/auth/use-auth";
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
  if (!user) return null;

  return (
    <>
      <PageHeader title="Profile" description="Your account details." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Account</CardTitle>
          </CardHeader>
          <CardContent className="divide-y">
            <Row
              label="Email"
              value={
                <span className="inline-flex items-center gap-1">
                  {user.email}
                  {user.is_verified ? (
                    <Badge variant="success">Verified</Badge>
                  ) : (
                    <Badge variant="warning">Unverified</Badge>
                  )}
                </span>
              }
            />
            <Row label="Full name" value={user.full_name || "—"} />
            <Row label="Role" value={<StatusBadge status={user.role} />} />
            <Row
              label="Status"
              value={<StatusBadge status={user.is_active ? "active" : "archived"} />}
            />
            <Row label="Last login" value={formatDateTime(user.last_login_at) || "—"} />
            <Row
              label="User ID"
              value={
                <span className="inline-flex items-center gap-1 font-mono text-xs">
                  {user.id}
                  <CopyButton value={user.id} label="Copy user id" />
                </span>
              }
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Access</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>Create personal API keys for programmatic access to the API.</p>
            <Button variant="outline" asChild>
              <Link to="/api-keys">
                <KeyRound className="h-4 w-4" /> Manage API keys
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
