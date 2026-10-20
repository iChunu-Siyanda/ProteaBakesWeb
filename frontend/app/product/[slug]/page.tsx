import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getProduct } from "@/lib/api/catalogue";
import { formatZAR } from "@/lib/utils";
import { ProductGallery } from "@/components/shop/ProductGallery";
import { AddToCartButton } from "@/components/shop/AddToCartButton";
import { Rating } from "@/components/shop/Rating";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const product = await getProduct(slug);
  if (!product) return { title: "Product not found" };
  return {
    title: product.name,
    description: product.description.slice(0, 160),
  };
}

export default async function ProductPage({ params }: Props) {
  const { slug } = await params;
  const product = await getProduct(slug);
  if (!product) notFound();

  return (
    <div className="container-page py-section">
      <nav aria-label="Breadcrumb" className="mb-8 text-sm text-muted">
        <Link href="/shop" className="hover:text-foreground">
          Shop
        </Link>
        {product.category && (
          <>
            {" / "}
            <Link
              href={`/shop?category=${product.category.slug}`}
              className="hover:text-foreground"
            >
              {product.category.name}
            </Link>
          </>
        )}
      </nav>

      <div className="grid gap-10 lg:grid-cols-2 lg:gap-16">
        <ProductGallery images={product.images} name={product.name} />

        <div className="space-y-6">
          <div className="space-y-2">
            <h1 className="font-serif text-4xl md:text-5xl">{product.name}</h1>
            <p className="text-2xl">{formatZAR(Number(product.price))}</p>
            <Rating value={product.average_rating} count={product.review_count} />
          </div>

          {product.is_made_to_order && (
            <p className="bg-accent-soft px-4 py-3 text-sm">
              Made to order. See{" "}
              <Link href="/how-ordering-works" className="underline">
                how ordering works
              </Link>{" "}
              for lead times.
            </p>
          )}

          <AddToCartButton product={product} />

          <p className="whitespace-pre-line leading-relaxed text-muted">
            {product.description}
          </p>

          <p className="border-t border-line pt-4 text-sm text-muted">
            Allergen details:{" "}
            <Link href="/allergens" className="underline">
              view our allergen guide
            </Link>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
