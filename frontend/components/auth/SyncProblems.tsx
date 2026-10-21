import { ButtonLink } from "@/components/ui/Button";
import type { SyncProblem } from "@/lib/cart/syncCart";

export function SyncProblems({ problems, next }: { problems: SyncProblem[]; next: string }) {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl">You&apos;re logged in</h1>
      <p>Some items from your cart could not be added:</p>
      <ul className="list-disc space-y-1 pl-5">
        {problems.map((p) => (
          <li key={p.productId}>
            <strong>{p.name}</strong>: {p.message}
          </li>
        ))}
      </ul>
      <ButtonLink href={next}>Continue</ButtonLink>
    </div>
  );
}
