"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import type { Product } from "@/lib/types";
import { addToCart } from "@/lib/cart/addToCart";


export function AddToCartButton({ product }: { product: Product }) {
  const { toast } = useToast();
  const [qty, setQty] = useState(1);

  async function handleAdd() {
    // setBusy(true) if you have it
    try {
      await addToCart(
        {
          id: product.id,
          name: product.name,
          slug: product.slug,
          price: product.price,
          image: null, // set to the first image URL from your Product type
        },
        1,
      );
      // your existing success toast, e.g. "Added to cart"
    } catch (e) {
      // your existing error toast with: e instanceof Error ? e.message : "Could not add to cart"
    } finally {
      // setBusy(false)
    }
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
