"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api/client";
import { Spinner } from "@/components/ui/Spinner";
import { ButtonLink } from "@/components/ui/Button";
import { formatZAR } from "@/lib/utils";
import type { Order } from "@/lib/checkout/types";

export function OrderView({
  orderNumber,
  placed,
}: {
  orderNumber: string;
  placed: boolean;
}) {
  const router = useRouter();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    apiFetch<Order>(`/orders/${encodeURIComponent(orderNumber)}`)
      .then((o) => !cancelled && setOrder(o))
      .catch((e: { status?: number }) => {
        if (cancelled) return;
        if (e?.status === 401) {
          router.replace(
            `/login?next=${encodeURIComponent(`/orders/${orderNumber}`)}`,
          );
        } else if (e?.status === 404) {
          setError("We couldn't find that order.");
        } else {
          setError("We couldn't load this order. Please try again.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [orderNumber, router]);

  if (error) return <p className="text-danger">{error}</p>;
  if (!order) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    );
  }

  const f = order.fulfillment;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {placed && (
        <div className="rounded-lg border border-accent/40 bg-surface p-5">
          <h1 className="text-2xl font-semibold">Thank you, order placed!</h1>
          <p className="mt-1 text-muted">
            Your order number is <strong>{order.order_number}</strong>.
          </p>
        </div>
      )}
      {!placed && (
        <h1 className="text-2xl font-semibold">Order {order.order_number}</h1>
      )}

      <div className="flex flex-wrap gap-x-8 gap-y-1 text-sm">
        <span>
          Status: <strong>{order.status}</strong>
        </span>
        <span>
          Payment: <strong>{order.payment?.status ?? "Awaiting payment"}</strong>
        </span>
      </div>

      <section className="rounded-lg border border-foreground/25 bg-surface p-5">
        <ul className="divide-y divide-foreground/10">
          {order.items.map((item) => (
            <li key={item.id} className="flex justify-between gap-4 py-2 text-sm">
              <span>
                {item.product_name}{" "}
                <span className="text-muted">× {item.quantity}</span>
              </span>
              <span>{formatZAR(Number(item.subtotal))}</span>
            </li>
          ))}
        </ul>
        <dl className="mt-4 space-y-1 border-t border-foreground/25 pt-4 text-sm">
          <div className="flex justify-between">
            <dt>Subtotal</dt>
            <dd>{formatZAR(Number(order.subtotal))}</dd>
          </div>
          {Number(order.discount_amount) > 0 && (
            <div className="flex justify-between">
              <dt>Discount</dt>
              <dd>−{formatZAR(Number(order.discount_amount))}</dd>
            </div>
          )}
          <div className="flex justify-between">
            <dt>Delivery</dt>
            <dd>{formatZAR(Number(order.delivery_fee))}</dd>
          </div>
          <div className="flex justify-between text-base font-semibold">
            <dt>Total</dt>
            <dd>{formatZAR(Number(order.total))}</dd>
          </div>
        </dl>
      </section>

      {f && (
        <section className="rounded-lg border border-foreground/25 bg-surface p-5 text-sm">
          <h2 className="mb-2 font-semibold">
            {f.type === "PICKUP" ? "Collection" : "Delivery"}
          </h2>
          {f.type === "PICKUP" ? (
            <p>
              {f.scheduled_date} at {f.scheduled_time?.slice(0, 5)}
            </p>
          ) : (
            <p>
              {f.recipient_name}
              <br />
              {f.address_line_1}
              {f.address_line_2 ? `, ${f.address_line_2}` : ""}
              <br />
              {f.city}, {f.province} {f.postal_code}
            </p>
          )}
        </section>
      )}

      <ButtonLink href="/shop" variant="outline">
        Continue shopping
      </ButtonLink>
    </div>
  );
}
