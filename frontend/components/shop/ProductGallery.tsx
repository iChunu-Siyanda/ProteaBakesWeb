"use client";

import Image from "next/image";
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { ProductImage } from "@/lib/types";

export function ProductGallery({
  images,
  name,
}: {
  images: ProductImage[];
  name: string;
}) {
  const sorted = [...images].sort((a, b) => a.position - b.position);
  const [index, setIndex] = useState(0);

  if (sorted.length === 0) {
    return (
      <div className="flex aspect-square items-center justify-center bg-surface font-serif text-2xl text-muted">
        Protea Bakes
      </div>
    );
  }

  const current = sorted[index];

  return (
    <div className="space-y-3">
      <div className="relative aspect-square overflow-hidden bg-surface">
        <Image
          src={current.image}
          alt={current.alt_text || name}
          fill
          priority
          sizes="(min-width: 1024px) 50vw, 100vw"
          className="object-cover"
        />
      </div>
      {sorted.length > 1 && (
        <div className="grid grid-cols-5 gap-2">
          {sorted.map((img, i) => (
            <button
              key={img.id}
              type="button"
              onClick={() => setIndex(i)}
              aria-label={`Show image ${i + 1} of ${sorted.length}`}
              aria-current={i === index}
              className={cn(
                "relative aspect-square overflow-hidden border-2",
                i === index ? "border-accent" : "border-transparent"
              )}
            >
              <Image
                src={img.image}
                alt=""
                fill
                sizes="100px"
                className="object-cover"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
