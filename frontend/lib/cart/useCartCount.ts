"use client";

import { useGuestCart } from "./useGuestCart";
import { useServerCart } from "./useServerCart";

export function useCartCount(): number {
  const guest = useGuestCart();
  const server = useServerCart();
  if (server.status === "server" && server.cart) {
    return server.cart.items.reduce((n, i) => n + i.quantity, 0);
  }
  return guest.count;
}
