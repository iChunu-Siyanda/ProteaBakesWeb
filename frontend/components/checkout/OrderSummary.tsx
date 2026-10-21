import Link from "next/link";
import { formatZAR } from "@/lib/utils";
import type { CheckoutCart } from "@/lib/checkout/types";

export function OrderSummary({ cart }: { cart: CheckoutCart }) {
  return (
    <aside className="rounded-lg border border-foreground/25 bg-surface p-5">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="text-lg font-semibold">Order summary</h2>
        <Link href="/cart" className="text-sm underline">
          Edit cart
        </Link>
      </div>

      <ul className="divide-y divide-foreground/10">
        {cart.items.map((item) => (
          <li key={item.id} className="flex justify-between gap-4 py-2 text-sm">
            <span>
              {item.product_name}{" "}
              <span className="text-muted">× {item.quantity}</span>
            </span>
            <span>{formatZAR(Number(item.subtotal))}</span>
          </li>
        ))}
      </ul>

      <div className="mt-4 flex justify-between border-t border-foreground/25 pt-4 font-semibold">
        <span>Subtotal</span>
        <span>{formatZAR(Number(cart.total))}</span>
      </div>
      <p className="mt-2 text-xs text-muted">
        Delivery fee and any promotion discount are calculated when you place
        the order.
      </p>
    </aside>
  );
}
