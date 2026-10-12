import { getGuestCart, removeFromGuestCart } from "./guestCart";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type SyncProblem = { productId: number; name: string; message: string };
export type SyncResult = { added: number; problems: SyncProblem[] };

function messageFrom(data: unknown): string {
  if (data && typeof data === "object") {
    const d = data as Record<string, unknown>;
    if (typeof d.detail === "string") return d.detail;
    const first = Object.values(d)[0];
    if (Array.isArray(first) && typeof first[0] === "string") return first[0];
  }
  return "This item could not be added to your cart.";
}

async function run(accessToken: string): Promise<SyncResult> {
  const result: SyncResult = { added: 0, problems: [] };

  // Sequential on purpose: each item is removed from the guest cart as soon as
  // the server has it, so a retry after a failure can never add it twice.
  for (const item of getGuestCart()) {
    const res = await fetch(`${API_URL}/api/cart/items/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ product: item.productId, quantity: item.quantity }),
    });

    if (res.status === 401) {
      // Token problem: stop and keep the remaining items for the next attempt.
      throw new Error("Your session has expired. Please log in again.");
    }

    if (res.ok) {
      result.added += 1;
    } else {
      const data = await res.json().catch(() => null);
      // e.g. sold out, only N left, or product no longer available.
      result.problems.push({
        productId: item.productId,
        name: item.name,
        message: messageFrom(data),
      });
    }

    // Processed either way. Problems are reported once instead of leaving
    // stale items in the guest cart.
    removeFromGuestCart(item.productId);
  }

  return result;
}

let inFlight: Promise<SyncResult> | null = null;

// Call right after a successful login or registration. Safe to call twice
// (React StrictMode): concurrent calls share one run.
export function syncGuestCartToServer(accessToken: string): Promise<SyncResult> {
  if (!inFlight) {
    inFlight = run(accessToken).finally(() => {
      inFlight = null;
    });
  }
  return inFlight;
}
