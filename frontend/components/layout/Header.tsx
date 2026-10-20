"use client";

import { useSession } from "@/lib/auth/useSession";
import { useCartCount } from "@/lib/cart/useCartCount";
import Link from "next/link";
import { useEffect, useState } from "react";


const NAV = [
  { href: "/shop", label: "Shop" },
  { href: "/our-story", label: "Our Story" },
  { href: "/how-ordering-works", label: "How It Works" },
  { href: "/delivery-and-pickup", label: "Delivery & Pickup" },
];

const svg = {
  width: 22,
  height: 22,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

const iconLink =
  "relative inline-flex h-10 w-10 items-center justify-center rounded-full hover:bg-surface";

export function Header() {
  const [open, setOpen] = useState(false);
  const authenticated = useSession();
  const count = useCartCount();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-background/95 backdrop-blur">
      <div className="mx-auto grid h-16 max-w-page grid-cols-[1fr_auto_1fr] items-center px-4 sm:px-6">
        <div className="flex items-center">
          <button
            type="button"
            className="-ml-2 inline-flex h-10 w-10 items-center justify-center rounded-full hover:bg-surface md:hidden"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            aria-controls="mobile-menu"
            onClick={() => setOpen((v) => !v)}
          >
            <svg {...svg}>
              {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
          <nav aria-label="Main" className="hidden gap-8 text-sm md:flex">
            {NAV.map((l) => (
              <Link key={l.href} href={l.href} className="hover:text-accent">
                {l.label}
              </Link>
            ))}
          </nav>
        </div>

        <Link href="/" className="font-serif text-2xl tracking-wide sm:text-3xl">
          Protea Bakes
        </Link>

        <div className="flex items-center justify-end gap-1">
          <Link
            href={authenticated ? "/account" : "/login"}
            className={iconLink}
            aria-label={authenticated ? "Account" : "Sign in"}
          >
            <svg {...svg}>
              <circle cx="12" cy="8" r="4" />
              <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
            </svg>
          </Link>
          <Link
            href="/cart"
            className={iconLink}
            aria-label={count > 0 ? `Cart, ${count} item${count === 1 ? "" : "s"}` : "Cart"}
          >
            <svg {...svg}>
              <path d="M6 8h12l-1 12H7L6 8Z" />
              <path d="M9 8V6a3 3 0 0 1 6 0v2" />
            </svg>
            {count > 0 && (
              <span
                aria-hidden="true"
                className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] text-white"
              >
                {count}
              </span>
            )}
          </Link>
        </div>
      </div>

      {open && (
        <nav id="mobile-menu" aria-label="Mobile" className="border-t border-line bg-background md:hidden">
          <ul className="mx-auto max-w-page px-4 py-2 sm:px-6">
            {NAV.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="block border-b border-line py-4 font-serif text-xl last:border-b-0"
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </header>
  );
}
