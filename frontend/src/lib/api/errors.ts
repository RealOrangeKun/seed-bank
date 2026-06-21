/**
 * RFC 9457 Problem Details — the API's error contract
 * (Content-Type: application/problem+json). See backend `api/errors.py`.
 */
export interface ProblemFieldError {
  field: string;
  message: string;
  code: string;
}

export interface Problem {
  type: string;
  title: string;
  status: number;
  detail?: string | null;
  code: string;
  request_id?: string | null;
  errors?: ProblemFieldError[] | null;
}

/** Thrown by the API client for any non-2xx response. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly problem: Problem | null;
  readonly fieldErrors: ProblemFieldError[];
  readonly requestId: string | null;

  constructor(status: number, problem: Problem | null, fallback?: string) {
    super(problem?.detail || problem?.title || fallback || `Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.code = problem?.code ?? "unknown";
    this.problem = problem;
    this.fieldErrors = problem?.errors ?? [];
    this.requestId = problem?.request_id ?? null;
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

/** Build an ApiError from a fetch Response (reads the problem+json body). */
export async function apiErrorFromResponse(res: Response): Promise<ApiError> {
  let problem: Problem | null = null;
  try {
    const body = (await res.clone().json()) as Problem;
    if (body && typeof body === "object" && "status" in body) problem = body;
  } catch {
    // Non-JSON body (e.g. a proxy 502). Fall back to status text.
  }
  return new ApiError(res.status, problem, res.statusText);
}
