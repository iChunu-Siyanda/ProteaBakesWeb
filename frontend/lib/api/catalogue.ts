import { apiGet } from "@/lib/api/server";
import { ApiError } from "@/lib/api/errors";
import type { Category, Product, ProductQuery } from "@/lib/types";

type List<T> = T[] | { results: T[] };

function unwrap<T>(data: List<T>): T[] {
  return Array.isArray(data) ? data : data.results;
}

export async function getProducts(query: ProductQuery = {}): Promise<Product[]> {
  const params = new URLSearchParams();
  if (query.category) params.set("category", query.category);
  if (query.search) params.set("search", query.search);
  if (query.ordering) params.set("ordering", query.ordering);
  const qs = params.toString();
  const data = await apiGet<List<Product>>(`/products/${qs ? `?${qs}` : ""}`, {
    revalidate: 60,
  });
  return unwrap(data);
}

export async function getCategories(): Promise<Category[]> {
  const data = await apiGet<List<Category>>("/categories/", { revalidate: 300 });
  return unwrap(data);
}

export async function getProduct(slug: string): Promise<Product | null> {
  try {
    return await apiGet<Product>(
      `/products/slug/${encodeURIComponent(slug)}/`,
      { revalidate: 60 }
    );
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}
