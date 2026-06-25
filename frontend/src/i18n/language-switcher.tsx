import { Check, Languages } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

import { LOCALE_LABEL, LOCALES } from "./locale";
import { useI18n } from "./use-i18n";

/**
 * Language picker. The trigger always shows the *other* language's native name
 * so a non-reader can recognize and reach their language in one tap, and the
 * menu lists every locale with a check on the active one.
 */
export function LanguageSwitcher({ className }: { className?: string }) {
  const { locale, setLocale, t } = useI18n();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn("gap-2", className)}
          aria-label={t("common.language")}
        >
          <Languages className="h-4 w-4" />
          <span className="text-sm font-medium">{LOCALE_LABEL[locale]}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-40">
        {LOCALES.map((loc) => (
          <DropdownMenuItem
            key={loc}
            onClick={() => setLocale(loc)}
            className="justify-between"
          >
            <span dir={loc === "ar" ? "rtl" : "ltr"}>{LOCALE_LABEL[loc]}</span>
            {loc === locale ? <Check className="h-4 w-4 text-primary" /> : null}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
