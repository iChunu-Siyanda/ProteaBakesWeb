import Image from "next/image";
import Link from "next/link";
import { formatZAR } from "@/lib/utils";
import type { Product } from "@/lib/types";
import { Rating } from "@/components/shop/Rating";

export function ProductCard({
  product,
  priority = false,
}: {
  product: Product;
  priority?: boolean;
}) {
  const img = [...product.images].sort((a, b) => a.position - b.position)[0];

  return (
    <Link href={`/product/${product.slug}`} className="group block">
      <div className="relative aspect-[4/5] overflow-hidden bg-surface">
        {img ? (
          <Image
            src={img.image}
            alt={img.alt_text || product.name}
            fill
            priority={priority}
            sizes="(min-width: 1024px) 25vw, (min-width: 640px) 33vw, 50vw"
            className="object-cover transition duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center font-serif text-2xl text-muted">
            Protea Bakes
          </div>
        )}
        {!product.is_available && (
          <span className="absolute left-3 top-3 bg-background px-2 py-1 text-xs uppercase tracking-wide">
            Sold out
          </span>
        )}
      </div>
      <div className="mt-3 space-y-1">
        <h3 className="font-serif text-lg leading-tight">{product.name}</h3>
        <p className="text-sm text-muted">{formatZAR(Number(product.price))}</p>
        <Rating value={product.average_rating} count={product.review_count} />
      </div>
    </Link>
  );
}
