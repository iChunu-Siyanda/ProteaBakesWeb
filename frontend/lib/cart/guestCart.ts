// Guest cart: lives in the browser (localStorage) until the customer logs in.
// Prices stored here are for display only. The server always recalculates
// prices from the database when the items are sent to the real cart.

export type GuestCartItem = {
  productId: number;
  name: string;
  slug: string;
  price: string; // e.g. "320.00" (as returned by the API)
  image?: string | null;
  quantity: number;
};

const KEY = "proteabakes.guestCart.v1";
const EVENT = "proteabakes:guestcart";
const MAX_QTY = 99;

export const EMPTY_GUEST_CART: GuestCartItem[] = [];

let cachedRaw: string | null = null;
let cachedItems: GuestCartItem[] = EMPTY_GUEST_CART;

function isValid(x: unknown): x is GuestCartItem {
  const i = x as GuestCartItem;
  return (
    !!i &&
    Number.isInteger(i.productId) &&
    Number.isInteger(i.quantity) &&
    i.quantity >= 1 &&
    typeof i.name === "string" &&
    typeof i.price === "string"
  );
}

// Returns the same array object until the stored data changes, which is what
// React's useSyncExternalStore needs.
export function getGuestCart(): GuestCartItem[] {
  if (typeof window === "undefined") return EMPTY_GUEST_CART;

  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(KEY);
  } catch {
    return EMPTY_GUEST_CART; // storage blocked (private mode etc.)
  }

  if (raw === cachedRaw) return cachedItems;

  cachedRaw = raw;
  try {
    const parsed = raw ? JSON.parse(raw) : [];
    cachedItems = Array.isArray(parsed) ? parsed.filter(isValid) : EMPTY_GUEST_CART;
  } catch {
    cachedItems = EMPTY_GUEST_CART;
  }
  return cachedItems;
}

function write(items: GuestCartItem[]) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(items));
  } catch {
    /* ignore: cart simply won't persist */
  }
  window.dispatchEvent(new Event(EVENT));
}

export function subscribeGuestCart(callback: () => void): () => void {
  const onStorage = (e: StorageEvent) => {
    if (e.key === KEY || e.key === null) callback(); // other tabs
  };
  window.addEventListener(EVENT, callback);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(EVENT, callback);
    window.removeEventListener("storage", onStorage);
  };
}

export function addToGuestCart(
  item: Omit<GuestCartItem, "quantity">,
  quantity = 1,
) {
  const items = [...getGuestCart()];
  const existing = items.find((i) => i.productId === item.productId);

  if (existing) {
    existing.quantity = Math.min(existing.quantity + quantity, MAX_QTY);
  } else {
    items.push({ ...item, quantity: Math.min(quantity, MAX_QTY) });
  }
  write(items);
}

export function setGuestQuantity(productId: number, quantity: number) {
  if (quantity <= 0) return removeFromGuestCart(productId);
  write(
    getGuestCart().map((i) =>
      i.productId === productId
        ? { ...i, quantity: Math.min(quantity, MAX_QTY) }
        : i,
    ),
  );
}

export function removeFromGuestCart(productId: number) {
  write(getGuestCart().filter((i) => i.productId !== productId));
}

export function clearGuestCart() {
  write([]);
}

export function guestCartCount(items: GuestCartItem[]): number {
  return items.reduce((n, i) => n + i.quantity, 0);
}

// Display subtotal in cents (avoids floating point rounding problems).
export function guestCartSubtotalCents(items: GuestCartItem[]): number {
  return items.reduce(
    (sum, i) => sum + Math.round(parseFloat(i.price) * 100) * i.quantity,
    0,
  );
}
