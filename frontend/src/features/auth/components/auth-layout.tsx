import { ThemeToggle } from "@/components/theme/theme-toggle";

interface AuthLayoutProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

/** Centered card on the agricultural field backdrop, for unauthenticated pages. */
export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className="bg-field flex min-h-screen flex-col items-center justify-center p-4">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <img src="/seed.svg" alt="" className="h-12 w-12" />
          <h1 className="text-xl font-semibold">Seed-Bank</h1>
        </div>
        <div className="rounded-xl border bg-card p-6 shadow-sm">
          <div className="mb-5 space-y-1 text-center">
            <h2 className="text-lg font-semibold">{title}</h2>
            {subtitle ? (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            ) : null}
          </div>
          {children}
        </div>
        {footer ? (
          <p className="mt-4 text-center text-sm text-muted-foreground">{footer}</p>
        ) : null}
      </div>
    </div>
  );
}
