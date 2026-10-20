import Link from "next/link";

const COLS = [
  {
    title: "Shop",
    links: [
      { href: "/shop", label: "All products" },
      { href: "/how-ordering-works", label: "How ordering works" },
      { href: "/delivery-and-pickup", label: "Delivery & pickup" },
    ],
  },
  {
    title: "Help",
    links: [
      { href: "/faq", label: "FAQ" },
      { href: "/contact", label: "Contact" },
      { href: "/allergens", label: "Allergens" },
      { href: "/refund-policy", label: "Refunds & cancellations" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="mt-section border-t border-line">
      <div className="mx-auto grid max-w-page gap-10 px-4 py-12 sm:px-6 md:grid-cols-[2fr_1fr_1fr]">
        <div>
          <p className="font-serif text-2xl">Protea Bakes</p>
          <p className="mt-2 max-w-xs text-sm text-muted">Handmade, baked to order.</p>
        </div>
        {COLS.map((c) => (
          <nav key={c.title} aria-label={c.title}>
            <p className="text-sm font-medium">{c.title}</p>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              {c.links.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="hover:text-accent">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <p className="border-t border-line py-6 text-center text-xs text-muted">
        © {new Date().getFullYear()} Protea Bakes. All rights reserved.
      </p>
    </footer>
  );
}
