export function Rating({
  value,
  count,
}: {
  value: number | null;
  count: number;
}) {
  if (value === null || count === 0) return null;
  const rounded = Math.round(value);
  return (
    <div
      className="flex items-center gap-2 text-sm text-muted"
      aria-label={`Rated ${value} out of 5 from ${count} reviews`}
    >
      <span aria-hidden className="tracking-wider text-accent">
        {"★".repeat(rounded)}
        <span className="text-line">{"★".repeat(5 - rounded)}</span>
      </span>
      <span>
        {value.toFixed(1)} ({count})
      </span>
    </div>
  );
}
