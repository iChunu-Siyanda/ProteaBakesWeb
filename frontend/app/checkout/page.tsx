"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/auth/useSession";
import { apiFetch } from "@/lib/api/client";
import { Spinner } from "@/components/ui/Spinner";
import { ButtonLink } from "@/components/ui/Button";
import { CheckoutForm } from "@/components/checkout/CheckoutForm";
import type { CheckoutCart } from "@/lib/checkout/types";
import { OrderSummary } from "@/components/checkout/OrderSummary";

export default function CheckoutPage() {
  const router = useRouter();
  const session = useSession();
  const [cart, setCart] = useState<CheckoutCart | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (session === false) router.replace("/login?next=/checkout");
  }, [session, router]);

  useEffect(() => {
    if (session !== true) return;
    let cancelled = false;
    apiFetch<CheckoutCart>("/cart")
      .then((c) => !cancelled && setCart(c))
      .catch((e: { status?: number }) => {
        if (cancelled) return;
        if (e?.status === 401) router.replace("/login?next=/checkout");
        else setError("We couldn't load your cart. Please try again.");
      });
    return () => {
      cancelled = true;
    };
  }, [session, router]);

  let body: React.ReactNode;
  if (session !== true || (!cart && !error)) {
    body = (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  } else if (error) {
    body = <p className="text-danger">{error}</p>;
  } else if (!cart || cart.items.length === 0) {
    body = (
      <div className="py-16 text-center">
        <p className="mb-4 text-muted">Your cart is empty.</p>
        <ButtonLink href="/shop">Browse the shop</ButtonLink>
      </div>
    );
  } else {
    body = (
      <div className="grid gap-8 lg:grid-cols-[1fr_380px]">
        <CheckoutForm />
        <OrderSummary cart={cart} />
      </div>
    );
  }

  return (
    <main className="container-page py-10">
      <h1 className="mb-6 text-3xl font-semibold">Checkout</h1>
      {body}
    </main>
  );
}
