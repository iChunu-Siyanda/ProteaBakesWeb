import { apiFetch } from "@/lib/api/client";
import { addToGuestCart } from "./guestCart";
import { refreshServerCart, statusOf } from "./useServerCart";

export type CartProduct = {
  id: string;
  name: string;
  slug: string;
  price: string;
  image?: string | null;
};

// Logged in -> server cart. Not logged in (401) -> guest cart.
export async function addToCart(p: CartProduct, quantity = 1): Promise<"server" | "guest"> {
  try {
    await apiFetch("/cart/items", { method: "POST", json: { product: p.id, quantity } });
    await refreshServerCart();
    return "server";
  } catch (e) {
    if (statusOf(e) === 401) {
      const id = Number(p.id);

      if (!Number.isInteger(id)) {
        throw new Error(`Invalid product id: ${p.id}`);
      }
      
      addToGuestCart(
        { productId: id, name: p.name, slug: p.slug, price: p.price, image: p.image },
        quantity,
      );
      return "guest";
    }
    throw e; // sold out, inactive product, etc.
  }
}
