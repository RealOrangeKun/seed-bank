/**
 * Typed access to build-time environment. Never read `import.meta.env`
 * directly elsewhere — funnel through here so there is one place to validate
 * and one place to change (mirrors the backend's single-Settings rule).
 */
function required(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(
      `Missing required env var ${name}. Copy .env.example to .env and set it.`,
    );
  }
  return value.replace(/\/$/, "");
}

export const env = {
  /**
   * API origin, e.g. `http://localhost:8000` — WITHOUT the version prefix.
   * The generated OpenAPI `paths` already carry `/api/v1/...`, so the client
   * base URL is the origin only (otherwise the prefix would double up).
   */
  apiOrigin: required("VITE_API_BASE_URL", import.meta.env.VITE_API_BASE_URL),
} as const;
