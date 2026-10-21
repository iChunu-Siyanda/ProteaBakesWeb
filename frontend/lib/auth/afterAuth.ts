import { notifySessionChange } from "./useSession";
import { syncGuestCartToServer, type SyncResult } from "@/lib/cart/syncCart";

// Run after a successful login/register (cookies are already set).
export async function completeAuth(): Promise<SyncResult> {
  notifySessionChange();
  try {
    return await syncGuestCartToServer();
  } catch {
    return { added: 0, problems: [] }; // leftover guest items stay for next time
  }
}

// Maps Django errors ({email:["..."]}, {detail:"..."}) to field + general messages.
export function parseFormErrors(data: unknown) {
  const fields: Record<string, string> = {};
  let general: string | undefined;
  if (data && typeof data === "object") {
    for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
      const msg = Array.isArray(v) ? v.find((x) => typeof x === "string") : v;
      if (typeof msg !== "string") continue;
      if (k === "detail" || k === "message" || k === "non_field_errors") general = msg;
      else fields[k] = msg;
    }
  }
  if (!general && Object.keys(fields).length === 0) {
    general = "Something went wrong. Please try again.";
  }
  return { fields, general };
}
