"use client";

import Link from "next/link";
import { useState } from "react";
import { useGuestCart } from "@/lib/cart/useGuestCart";
import { setGuestQuantity, removeFromGuestCart } from "@/lib/cart/guestCart";
import {
  useServerCart,
  setServerQuantity,
  removeServerItem,
} from "@/lib/cart/useServerCart";

const zar = (n: number) =>
  new Intl.NumberFormat("en-ZA", { style: "currency", currency: "ZAR" }).format(n);

type Row = {
  key: string;
  name: string;
  slug?: string;
  unit: number;
  quantity: number;
  setQty: (q: number) => Promise<void> | void;
  remove: () => Promise<void> | void;
};

export default function CartPage() {
  const guest = useGuestCart();
  const server = useServerCart();
  const [error, setError] = useState<string | null>(null);

  if (server.status === "loading") {
    return <main className="container-page py-10">Loading your cart…</main>;
  }

  const cart = server.status === "server" ? server.cart : null;

  const rows: Row[] = cart
    ? cart.items.map((i) => ({
        key: `s${i.id}`,
        name: i.product_name,
        slug: i.product_slug,
        unit: parseFloat(i.unit_price),
        quantity: i.quantity,
        setQty: (q) => (q <= 0 ? removeServerItem(i.id) : setServerQuantity(i.id, q)),
        remove: () => removeServerItem(i.id),
      }))
    : guest.items.map((i) => ({
        key: `g${i.productId}`,
        name: i.name,
        slug: i.slug,
        unit: parseFloat(i.price),
        quantity: i.quantity,
        setQty: (q) => setGuestQuantity(i.productId, q),
        remove: () => removeFromGuestCart(i.productId),
      }));

  const total = cart ? parseFloat(cart.total) : guest.subtotalCents / 100;

  async function run(fn: () => Promise<void> | void) {
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    }
  }

  if (rows.length === 0) {
    return (
      <main className="container-page py-10">
        <h1 className="text-2xl font-semibold">Your cart</h1>
        <p className="mt-4">Your cart is empty.</p>
        <Link href="/shop" className="mt-4 inline-block underline">
          Browse the shop
        </Link>
      </main>
    );
  }

  return (
    <main className="container-page py-10">
      <h1 className="text-2xl font-semibold">Your cart</h1>
      {error && <p role="alert" className="mt-4 text-red-700">{error}</p>}

      <ul className="mt-6 divide-y divide-black/10">
        {rows.map((r) => (
          <li key={r.key} className="flex items-center justify-between gap-4 py-4">
            <div className="min-w-0">
              {r.slug ? (
                <Link href={`/product/${r.slug}`} className="font-medium hover:underline">
                  {r.name}
                </Link>
              ) : (
                <span className="font-medium">{r.name}</span>
              )}
              <p className="text-sm opacity-70">{zar(r.unit)} each</p>
            </div>

            <div className="flex items-center gap-3">
              <button
                aria-label={`Decrease ${r.name}`}
                className="h-8 w-8 rounded border border-black/20"
                onClick={() => run(() => r.setQty(r.quantity - 1))}
              >
                −
              </button>
              <span className="w-6 text-center">{r.quantity}</span>
              <button
                aria-label={`Increase ${r.name}`}
                className="h-8 w-8 rounded border border-black/20"
                onClick={() => run(() => r.setQty(r.quantity + 1))}
              >
                +
              </button>
              <span className="w-24 text-right">{zar(r.unit * r.quantity)}</span>
              <button className="text-sm underline" onClick={() => run(r.remove)}>
                Remove
              </button>
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-6 flex items-center justify-between border-t border-black/10 pt-4">
        <span className="text-lg font-semibold">Total</span>
        <span className="text-lg font-semibold">{zar(total)}</span>
      </div>

      <Link
        href={cart ? "/checkout" : "/login?next=/checkout"}
        className="mt-6 inline-block rounded bg-black px-6 py-3 text-white"
      >
        {cart ? "Checkout" : "Log in to checkout"}
      </Link>
    </main>
  );
}
