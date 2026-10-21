"use client";

import { useEffect, useSyncExternalStore } from "react";
import { apiFetch } from "@/lib/api/client";

export type ServerCartItem = {
  id: number;
  product: number;
  product_name: string;
  product_slug?: string; // optional: see serializer note below
  unit_price: string;
  quantity: number;
  subtotal: string;
};
export type ServerCart = { id: number; status: string; items: ServerCartItem[]; total: string };
type State = { status: "loading" | "guest" | "server"; cart: ServerCart | null };

const LOADING: State = { status: "loading", cart: null };
let state: State = LOADING;
let started = false;
const listeners = new Set<() => void>();

function set(next: State) {
  state = next;
  listeners.forEach((l) => l());
}

export function statusOf(e: unknown): number | undefined {
  return (e as { status?: number } | null)?.status;
}

export async function refreshServerCart(): Promise<void> {
  try {
    const cart = await apiFetch<ServerCart>("/cart");
    set({ status: "server", cart });
  } catch (e) {
    const s = statusOf(e);
    if (s === 401 || s === 403 || state.status === "loading") {
      set({ status: "guest", cart: null });
    }
  }
}

// Call on logout.
export function resetServerCart() {
  set({ status: "guest", cart: null });
}

export async function setServerQuantity(itemId: number, quantity: number) {
  await apiFetch(`/cart/items/${itemId}`, { method: "PATCH", json: { quantity } });
  await refreshServerCart();
}

export async function removeServerItem(itemId: number) {
  await apiFetch(`/cart/items/${itemId}/delete`, { method: "DELETE" });
  await refreshServerCart();
}

export function useServerCart(): State {
  const s = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
    () => LOADING,
  );
  useEffect(() => {
    if (!started) {
      started = true;
      void refreshServerCart();
    }
  }, []);
  return s;
}
