import { apiFetch } from "@/lib/api/client";
import { getGuestCart, removeFromGuestCart } from "./guestCart";
import { refreshServerCart, statusOf } from "./useServerCart";

export type SyncProblem = { productId: number; name: string; message: string };
export type SyncResult = { added: number; problems: SyncProblem[] };

async function run(): Promise<SyncResult> {
  const result: SyncResult = { added: 0, problems: [] };

  // Sequential on purpose: each item leaves the guest cart once processed,
  // so a retry can never add it twice.
  for (const item of getGuestCart()) {
    try {
      await apiFetch("/cart/items", {
        method: "POST",
        json: { product: item.productId, quantity: item.quantity },
      });
      result.added += 1;
    } catch (e) {
      if (statusOf(e) === 401) {
        throw new Error("Your session has expired. Please log in again.");
      }
      result.problems.push({
        productId: item.productId,
        name: item.name,
        message: e instanceof Error ? e.message : "This item could not be added to your cart.",
      });
    }
    removeFromGuestCart(item.productId);
  }

  await refreshServerCart();
  return result;
}

let inFlight: Promise<SyncResult> | null = null;

// Call right after a successful login/registration. Concurrent calls
// (StrictMode) share one run.
export function syncGuestCartToServer(): Promise<SyncResult> {
  if (!inFlight) {
    inFlight = run().finally(() => {
      inFlight = null;
    });
  }
  return inFlight;
}
