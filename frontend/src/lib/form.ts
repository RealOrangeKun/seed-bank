import type { UseFormSetError, FieldValues, Path } from "react-hook-form";
import { toast } from "sonner";

import { isApiError } from "./api/errors";

/**
 * Surface an API error on a form: map RFC 9457 field errors (422) onto the
 * matching inputs, and toast anything else (auth, conflict, server). Keeps
 * error handling identical across every form in the app.
 */
export function applyApiError<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
): void {
  if (isApiError(error) && error.fieldErrors.length > 0) {
    for (const fe of error.fieldErrors) {
      setError(fe.field as Path<T>, { type: "server", message: fe.message });
    }
    return;
  }
  toast.error(
    isApiError(error)
      ? error.message
      : error instanceof Error
        ? error.message
        : "Request failed",
  );
}
