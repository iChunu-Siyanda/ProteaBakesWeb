import { Suspense } from "react";
import Link from "next/link";
import { getCategories, getProducts } from "@/lib/api/catalogue";
import { ORDERINGS, type Ordering } from "@/lib/types";
import { ProductCard } from "@/components/shop/ProductCard";
import { ShopFilters } from "@/components/shop/ShopFilters";

export const metadata = { title: "Shop" };

type Props = {
  searchParams: Promise<{ category?: string; search?: string; ordering?: string }>;
};

export default async function ShopPage({ searchParams }: Props) {
  const sp = await searchParams;
  const ordering = ORDERINGS.includes(sp.ordering as Ordering)
    ? (sp.ordering as Ordering)
    : undefined;

  const [products, categories] = await Promise.all([
    getProducts({ category: sp.category, search: sp.search, ordering }),
    getCategories(),
  ]);

  return (
    <div className="container-page py-section">
      <h1 className="font-serif text-4xl md:text-5xl">Shop</h1>

      <div className="mt-8">
        <Suspense fallback={null}>
          <ShopFilters categories={categories} />
        </Suspense>
      </div>

      {products.length === 0 ? (
        <div className="mt-16 text-center">
          <p className="font-serif text-2xl">Nothing here yet</p>
          <p className="mt-2 text-muted">
            Try a different search or category.
          </p>
          <Link href="/shop" className="mt-4 inline-block underline">
            Clear filters
          </Link>
        </div>
      ) : (
        <div className="mt-10 grid grid-cols-2 gap-x-4 gap-y-10 sm:grid-cols-3 lg:grid-cols-4 lg:gap-x-6">
          {products.map((p, i) => (
            <ProductCard key={p.id} product={p} priority={i < 4} />
          ))}
        </div>
      )}
    </div>
  );
}
