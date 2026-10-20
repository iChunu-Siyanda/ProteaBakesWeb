"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { Category } from "@/lib/types";

const SORTS = [
  { value: "", label: "A to Z" },
  { value: "newest", label: "Newest" },
  { value: "price", label: "Price: low to high" },
  { value: "-price", label: "Price: high to low" },
];

export function ShopFilters({ categories }: { categories: Category[] }) {
  const router = useRouter();
  const sp = useSearchParams();
  const active = sp.get("category") ?? "";
  const [search, setSearch] = useState(sp.get("search") ?? "");

  function href(patch: Record<string, string | null>) {
    const next = new URLSearchParams(sp.toString());
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    const qs = next.toString();
    return qs ? `/shop?${qs}` : "/shop";
  }

  const chip = (isActive: boolean) =>
    cn(
      "border px-4 py-2 text-sm transition-colors",
      isActive
        ? "border-accent bg-accent text-white"
        : "border-line hover:border-accent"
    );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        <Link href={href({ category: null })} className={chip(active === "")}>
          All
        </Link>
        {categories.map((c) => (
          <Link
            key={c.id}
            href={href({ category: c.slug })}
            className={chip(active === c.slug)}
          >
            {c.name}
          </Link>
        ))}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <form
          role="search"
          className="flex flex-1 gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            router.push(href({ search: search.trim() || null }));
          }}
        >
          <label htmlFor="shop-search" className="sr-only">
            Search products
          </label>
          <input
            id="shop-search"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search cakes, loaves, treats"
            className="w-full border border-line bg-background px-4 py-2 text-sm outline-none focus:border-accent"
          />
          <button
            type="submit"
            className="border border-line px-4 py-2 text-sm hover:border-accent"
          >
            Search
          </button>
        </form>

        <div>
          <label htmlFor="shop-sort" className="sr-only">
            Sort by
          </label>
          <select
            id="shop-sort"
            value={sp.get("ordering") ?? ""}
            onChange={(e) => router.push(href({ ordering: e.target.value || null }))}
            className="w-full border border-line bg-background px-4 py-2 text-sm outline-none focus:border-accent sm:w-auto"
          >
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
