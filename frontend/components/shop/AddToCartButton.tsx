"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import type { Product } from "@/lib/types";

export function AddToCartButton({ product }: { product: Product }) {
  const { toast } = useToast();
  const [qty, setQty] = useState(1);

  function handleAdd() {
    // TODO Section 2: call the real cart (guest + server) here.
    toast(`Cart wiring comes in Section 2 (${qty} x ${product.name})`, "info");
  }

  return (
    <div className="flex items-stretch gap-3">
      <div className="flex items-center border border-line">
        <button
          type="button"
          aria-label="Decrease quantity"
          onClick={() => setQty((q) => Math.max(1, q - 1))}
          className="px-3 py-2 text-lg"
        >
          −
        </button>
        <span className="w-8 text-center" aria-live="polite">
          {qty}
        </span>
        <button
          type="button"
          aria-label="Increase quantity"
          onClick={() => setQty((q) => Math.min(20, q + 1))}
          className="px-3 py-2 text-lg"
        >
          +
        </button>
      </div>
      <Button
        onClick={handleAdd}
        disabled={!product.is_available}
        className="flex-1"
      >
        {product.is_available ? "Add to cart" : "Sold out"}
      </Button>
    </div>
  );
}
