import { AlertTriangle, Inbox, Lock } from "lucide-react";

import { Spinner } from "@/components/ui/spinner";
import { useI18n } from "@/i18n";
import { isApiError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";

function Frame({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-card/50 p-10 text-center",
        className,
      )}
    >
      <div className="text-muted-foreground">{icon}</div>
      <div className="space-y-1">
        <p className="font-medium">{title}</p>
        {description ? (
          <p className="max-w-md text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}) {
  const { t } = useI18n();
  return (
    <Frame
      icon={<Inbox className="h-8 w-8" />}
      title={title ?? t("states.empty")}
      description={description}
      action={action}
    />
  );
}

export function ErrorState({ error, action }: { error: unknown; action?: React.ReactNode }) {
  const { t } = useI18n();
  const message = isApiError(error)
    ? error.message
    : error instanceof Error
      ? error.message
      : t("states.somethingWrong");
  const requestId = isApiError(error) ? error.requestId : null;
  return (
    <Frame
      icon={<AlertTriangle className="h-8 w-8 text-destructive" />}
      title={t("states.errorTitle")}
      description={
        requestId ? t("states.requestId", { message, id: requestId }) : message
      }
      action={action}
    />
  );
}

export function ForbiddenState() {
  const { t } = useI18n();
  return (
    <Frame
      className="m-6"
      icon={<Lock className="h-8 w-8" />}
      title={t("states.forbiddenTitle")}
      description={t("states.forbiddenDesc")}
    />
  );
}

export function LoadingState({ label }: { label?: string }) {
  const { t } = useI18n();
  return (
    <div className="flex items-center justify-center gap-2 p-10 text-sm text-muted-foreground">
      <Spinner className="text-primary" />
      {label ?? t("states.loading")}
    </div>
  );
}
