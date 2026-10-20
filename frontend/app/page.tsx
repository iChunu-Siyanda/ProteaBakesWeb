import Link from "next/link";
import { ButtonLink } from "@/components/ui/Button";
import { ProductCard } from "@/components/shop/ProductCard";
import { getCategories, getProducts } from "@/lib/api/catalogue";

export default async function HomePage() {
  const [newest, categories] = await Promise.all([
    getProducts({ ordering: "newest" }),
    getCategories(),
  ]);

  return (
    <>
      <section className="bg-accent-soft">
        <div className="container-page py-section text-center">
          <p className="text-sm uppercase tracking-[0.2em] text-muted">
            Handmade in small batches
          </p>
          <h1 className="mx-auto mt-4 max-w-3xl font-serif text-5xl leading-tight md:text-7xl">
            Baked fresh, made with care
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-muted">
            Cakes, loaves and treats for every occasion, baked to order.
          </p>
          <div className="mt-8">
            <ButtonLink href="/shop">Shop now</ButtonLink>
          </div>
        </div>
      </section>

      {categories.length > 0 && (
        <section className="container-page py-section">
          <h2 className="font-serif text-3xl">Browse by category</h2>
          <div className="mt-6 flex flex-wrap gap-3">
            {categories.map((c) => (
              <Link
                key={c.id}
                href={`/shop?category=${c.slug}`}
                className="border border-line px-5 py-3 transition-colors hover:border-accent"
              >
                {c.name}
              </Link>
            ))}
          </div>
        </section>
      )}

      {newest.length > 0 && (
        <section className="container-page pb-section">
          <div className="flex items-end justify-between">
            <h2 className="font-serif text-3xl">Fresh from the oven</h2>
            <Link href="/shop?ordering=newest" className="text-sm underline">
              View all
            </Link>
          </div>
          <div className="mt-8 grid grid-cols-2 gap-x-4 gap-y-10 lg:grid-cols-4 lg:gap-x-6">
            {newest.slice(0, 4).map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
