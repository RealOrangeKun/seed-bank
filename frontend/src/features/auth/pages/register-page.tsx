import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { Field } from "@/components/shared/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { applyApiError } from "@/lib/form";
import { register as registerApi } from "@/features/auth/api";

import { AuthLayout } from "../components/auth-layout";

// Mirrors the backend RegisterIn constraints (password 12–128, name ≤ 255).
const schema = z.object({
  full_name: z.string().max(255).optional(),
  email: z.string().email("Enter a valid email"),
  password: z
    .string()
    .min(12, "At least 12 characters")
    .max(128, "At most 128 characters"),
});
type FormValues = z.infer<typeof schema>;

export function RegisterPage() {
  const [done, setDone] = useState<string | null>(null);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", email: "", password: "" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const message = await registerApi({
        email: values.email,
        password: values.password,
        full_name: values.full_name?.trim() ? values.full_name : null,
      });
      setDone(message);
    } catch (err) {
      applyApiError(err, form.setError);
    }
  });

  if (done) {
    return (
      <AuthLayout
        title="Check your email"
        footer={
          <Link to="/login" className="font-medium text-primary hover:underline">
            Back to sign in
          </Link>
        }
      >
        <div className="flex flex-col items-center gap-3 text-center">
          <CheckCircle2 className="h-10 w-10 text-success" />
          <p className="text-sm text-muted-foreground">{done}</p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start analyzing seed quality in minutes"
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field
          id="full_name"
          label="Full name"
          error={form.formState.errors.full_name?.message}
        >
          <Input id="full_name" autoComplete="name" {...form.register("full_name")} />
        </Field>
        <Field id="email" label="Email" required error={form.formState.errors.email?.message}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            {...form.register("email")}
          />
        </Field>
        <Field
          id="password"
          label="Password"
          required
          hint="12–128 characters"
          error={form.formState.errors.password?.message}
        >
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            {...form.register("password")}
          />
        </Field>
        <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? <Spinner /> : null}
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
