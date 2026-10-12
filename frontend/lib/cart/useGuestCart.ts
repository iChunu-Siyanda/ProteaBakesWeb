"use client";

import { useSyncExternalStore } from "react";
import {
  EMPTY_GUEST_CART,
  getGuestCart,
  guestCartCount,
  guestCartSubtotalCents,
  subscribeGuestCart,
} from "./guestCart";

export function useGuestCart() {
  const items = useSyncExternalStore(
    subscribeGuestCart,
    getGuestCart,
    () => EMPTY_GUEST_CART, // server render: always empty
  );

  return {
    items,
    count: guestCartCount(items),
    subtotalCents: guestCartSubtotalCents(items),
  };
}
