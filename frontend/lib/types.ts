export type Category = { id: number | string; name: string; slug: string };

export type ProductImage = {
  id: number | string;
  image: string;
  alt_text: string;
  position: number;
};

export type Product = {
  id: number | string;
  name: string;
  slug: string;
  description: string;
  price: string | number; // DRF sends decimals as strings
  sku: string;
  category: Category | null;
  images: ProductImage[];
  is_active: boolean;
  is_made_to_order: boolean;
  is_available: boolean;
  average_rating: number | null;
  review_count: number;
};

export const ORDERINGS = ["name", "price", "-price", "newest"] as const;
export type Ordering = (typeof ORDERINGS)[number];

export type ProductQuery = {
  category?: string;
  search?: string;
  ordering?: Ordering;
};
