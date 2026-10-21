export type FieldErrors = Record<string, string>;
export interface ParsedError {
  status?: number;
  message: string;
  fields: FieldErrors;
}

function firstString(v: unknown): string | undefined {
  if (typeof v === "string") return v;
  if (Array.isArray(v)) return firstString(v[0]);
  return undefined;
}

/** Flattens DRF errors: {field: [..]}, {delivery_data: {city: [..]}}, {detail: ".."}. */
export function parseCheckoutError(err: unknown): ParsedError {
  const e = (err ?? {}) as {
    status?: number;
    message?: string;
    data?: unknown;
    body?: unknown;
    payload?: unknown;
    details?: unknown;
  };
  const body = (e.data ?? e.body ?? e.payload ?? e.details) as
    | Record<string, unknown>
    | undefined;

  const fields: FieldErrors = {};
  let message = "";

  if (body && typeof body === "object") {
    for (const [key, value] of Object.entries(body)) {
      if (key === "detail" || key === "non_field_errors") {
        message = firstString(value) ?? message;
      } else if (value && typeof value === "object" && !Array.isArray(value)) {
        for (const [k2, v2] of Object.entries(value)) {
          const s = firstString(v2);
          if (s) fields[k2] = s;
        }
      } else {
        const s = firstString(value);
        if (s) fields[key] = s;
      }
    }
  }

  if (!message && Object.keys(fields).length === 0) {
    message = e.message || "Could not place your order. Please try again.";
  }
  return { status: e.status, message, fields };
}
