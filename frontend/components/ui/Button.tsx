import Link from "next/link";
import { cn } from "@/lib/utils";
import { Spinner } from "./Spinner";

type Style = { variant?: "primary" | "outline" | "ghost"; size?: "md" | "lg"; className?: string };

export function buttonStyles({ variant = "primary", size = "md", className }: Style) {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-sm font-medium tracking-wide transition-colors disabled:pointer-events-none disabled:opacity-50",
    size === "lg" ? "h-12 px-8 text-base" : "h-10 px-6 text-sm",
    variant === "primary" && "bg-accent text-white hover:bg-accent-hover",
    variant === "outline" && "border border-foreground/25 text-foreground hover:border-foreground",
    variant === "ghost" && "text-foreground hover:bg-surface",
    className,
  );
}

export function Button({
  variant,
  size,
  className,
  loading,
  disabled,
  children,
  ...props
}: Style & { loading?: boolean } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonStyles({ variant, size, className })}
    >
      {loading && <Spinner className="h-4 w-4" label="Please wait" />}
      {children}
    </button>
  );
}

export function ButtonLink({
  variant,
  size,
  className,
  ...props
}: Style & React.ComponentProps<typeof Link>) {
  return <Link {...props} className={buttonStyles({ variant, size, className })} />;
}
