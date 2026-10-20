import { Spinner } from "@/components/ui/Spinner";

export default function Loading() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center text-muted">
      <Spinner className="h-6 w-6" />
    </div>
  );
}
