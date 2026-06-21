import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { Spinner } from "@/components/ui/spinner";
import { isApiError } from "@/lib/api/errors";
import { verifyEmail } from "@/features/auth/api";

import { AuthLayout } from "../components/auth-layout";

/** Consumes the `?token=` from the verification email link. */
export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";

  const query = useQuery({
    queryKey: ["verify-email", token],
    queryFn: () => verifyEmail(token),
    enabled: token.length > 0,
    retry: false,
  });

  return (
    <AuthLayout
      title="Email verification"
      footer={
        <Link to="/login" className="font-medium text-primary hover:underline">
          Continue to sign in
        </Link>
      }
    >
      <div className="flex flex-col items-center gap-3 text-center">
        {!token ? (
          <>
            <AlertTriangle className="h-10 w-10 text-destructive" />
            <p className="text-sm text-muted-foreground">
              Missing verification token. Use the link from your email.
            </p>
          </>
        ) : query.isPending ? (
          <>
            <Spinner className="h-8 w-8 text-primary" />
            <p className="text-sm text-muted-foreground">Verifying…</p>
          </>
        ) : query.isError ? (
          <>
            <AlertTriangle className="h-10 w-10 text-destructive" />
            <p className="text-sm text-muted-foreground">
              {isApiError(query.error)
                ? query.error.message
                : "Verification failed or the link expired."}
            </p>
          </>
        ) : (
          <>
            <CheckCircle2 className="h-10 w-10 text-success" />
            <p className="text-sm text-muted-foreground">{query.data}</p>
          </>
        )}
      </div>
    </AuthLayout>
  );
}
