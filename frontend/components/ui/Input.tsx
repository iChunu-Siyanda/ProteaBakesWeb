import { useId } from "react";
import { cn } from "@/lib/utils";

type Props = React.InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  hint?: string;
};

export function Input({ label, error, hint, className, id, ...props }: Props) {
  const auto = useId();
  const inputId = id ?? auto;
  const descId = `${inputId}-desc`;
  return (
    <div className="space-y-1.5">
      <label htmlFor={inputId} className="block text-sm">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? descId : undefined}
        className={cn(
          "h-11 w-full rounded-sm border bg-background px-3 text-base placeholder:text-muted/70",
          error ? "border-danger" : "border-foreground/25 hover:border-foreground/50",
          className,
        )}
        {...props}
      />
      {(error || hint) && (
        <p id={descId} role={error ? "alert" : undefined} className={cn("text-sm", error ? "text-danger" : "text-muted")}>
          {error ?? hint}
        </p>
      )}
    </div>
  );
}
