export type FieldErrors = Record<string, string[]>;

export class ApiError extends Error {
  status: number;
  fieldErrors: FieldErrors;
  constructor(status: number, message: string, fieldErrors: FieldErrors = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

export const GENERIC_ERROR = "Something went wrong. Please try again.";
export const NETWORK_ERROR = "We couldn't reach the server. Check your connection and try again.";

const FRIENDLY: Record<number, string> = {
  401: "Please sign in to continue.",
  403: "You don't have permission to do that.",
  404: "We couldn't find what you were looking for.",
  429: "Too many attempts. Please wait a moment and try again.",
};

/** Turns any Django/proxy response into an ApiError with a safe, friendly message. */
export function parseApiError(status: number, body: unknown): ApiError {
  const b = body && typeof body === "object" ? (body as Record<string, unknown>) : {};
  const fieldErrors: FieldErrors = {};
  for (const [key, value] of Object.entries(b)) {
    if (key === "detail" || key === "message") continue;
    const msgs = (Array.isArray(value) ? value : [value]).filter(
      (v): v is string => typeof v === "string",
    );
    if (msgs.length) fieldErrors[key] = msgs;
  }

  const detailOk = [400, 409, 422].includes(status);
  let message: string;
  if (typeof b.message === "string") message = b.message; // our own route handlers
  else if (detailOk && typeof b.detail === "string") message = b.detail; // e.g. stock problems
  else if (detailOk && fieldErrors.non_field_errors) message = fieldErrors.non_field_errors[0];
  else if (detailOk && Object.keys(fieldErrors).length) message = "Please check the highlighted fields.";
  else message = FRIENDLY[status] ?? GENERIC_ERROR;

  return new ApiError(status, message, fieldErrors);
}
