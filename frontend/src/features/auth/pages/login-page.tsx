import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { Field } from "@/components/shared/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useI18n } from "@/i18n";
import { applyApiError } from "@/lib/form";
import { fetchOAuthProviders, oauthLoginUrl } from "@/features/auth/api";
import { useAuth } from "@/features/auth/use-auth";

import { AuthLayout } from "../components/auth-layout";

interface FormValues {
  email: string;
  password: string;
}

export function LoginPage() {
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useI18n();
  const from = (location.state as { from?: Location } | null)?.from?.pathname ?? "/dashboard";

  // Reference data: which OAuth providers the backend has configured. A button
  // is rendered per provider, so a disabled provider simply never appears.
  const { data: providers = [] } = useQuery({
    queryKey: ["auth", "oauth-providers"],
    queryFn: fetchOAuthProviders,
    staleTime: 5 * 60 * 1000,
  });

  const providerLabel = (provider: string): string =>
    provider === "google" ? t("auth.continueWithGoogle") : provider;

  const schema = useMemo(
    () =>
      z.object({
        email: z.string().email(t("auth.invalidEmail")),
        password: z.string().min(1, t("auth.passwordRequired")),
      }),
    [t],
  );

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  if (status === "authenticated") return <Navigate to={from} replace />;

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await login(values.email, values.password);
      navigate(from, { replace: true });
    } catch (err) {
      applyApiError(err, form.setError);
    }
  });

  return (
    <AuthLayout
      title={t("auth.welcomeBack")}
      subtitle={t("auth.signInSubtitle")}
      footer={
        <>
          {t("auth.noAccount")}{" "}
          <Link to="/register" className="font-medium text-primary hover:underline">
            {t("auth.createOne")}
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field
          id="email"
          label={t("auth.email")}
          error={form.formState.errors.email?.message}
        >
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder={t("auth.emailPlaceholder")}
            {...form.register("email")}
          />
        </Field>
        <Field
          id="password"
          label={t("auth.password")}
          error={form.formState.errors.password?.message}
        >
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            {...form.register("password")}
          />
        </Field>
        <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? <Spinner /> : null}
          {t("common.signIn")}
        </Button>
      </form>

      {providers.length > 0 ? (
        <div className="mt-4 space-y-3">
          <div className="relative">
            <div className="absolute inset-0 flex items-center" aria-hidden="true">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">
                {t("auth.orContinueWith")}
              </span>
            </div>
          </div>
          {providers.map((provider) => (
            <Button
              key={provider}
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => {
                window.location.href = oauthLoginUrl(provider);
              }}
            >
              {providerLabel(provider)}
            </Button>
          ))}
        </div>
      ) : null}
    </AuthLayout>
  );
}
