export function cn(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

/** 320 -> "R 320.00", "1250" -> "R 1,250.00" */
export function formatZAR(value: number | string) {
  const n = typeof value === "string" ? parseFloat(value) : value;
  const safe = Number.isFinite(n) ? n : 0;
  return `R ${safe.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
