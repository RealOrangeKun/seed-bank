import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Spinner } from "@/components/ui/spinner";
import { useI18n } from "@/i18n";
import { useAuth } from "@/features/auth/use-auth";

import { AuthLayout } from "../components/auth-layout";

/**
 * Landing route for the backend OAuth callback. The backend completes the
 * provider exchange and 302s the browser here with the token pair in the URL
 * **fragment** (`#access_token=…&refresh_token=…`) — never sent to a server.
 * We read it, scrub the URL, complete the session, and route into the app. A
 * failed exchange arrives as `?error=…` and bounces back to login with a toast.
 */
export function OAuthCallbackPage() {
  const { loginWithTokens } = useAuth();
  const navigate = useNavigate();
  const { t } = useI18n();
  // StrictMode double-invokes effects in dev; guard so we consume the fragment
  // (which we scrub immediately) exactly once.
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    const fail = () => {
      toast.error(t("auth.oauthFailed"));
      navigate("/login", { replace: true });
    };

    if (new URLSearchParams(window.location.search).has("error")) {
      fail();
      return;
    }

    const params = new URLSearchParams(window.location.hash.slice(1));
    const access = params.get("access_token");
    const refresh = params.get("refresh_token");
    // Scrub tokens from the address bar + history before doing anything else.
    window.history.replaceState(null, "", window.location.pathname);

    if (!access || !refresh) {
      fail();
      return;
    }

    loginWithTokens(access, refresh)
      .then(() => navigate("/dashboard", { replace: true }))
      .catch(fail);
  }, [loginWithTokens, navigate, t]);

  return (
    <AuthLayout title={t("auth.signingIn")} subtitle={t("auth.oauthInProgress")}>
      <div className="flex justify-center py-6">
        <Spinner />
      </div>
    </AuthLayout>
  );
}
