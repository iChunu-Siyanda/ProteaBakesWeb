"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { completeAuth, parseFormErrors } from "@/lib/auth/afterAuth";
import type { SyncProblem } from "@/lib/cart/syncCart";
import { SyncProblems } from "./SyncProblems";

export function RegisterForm({ next }: { next: string }) {
  const router = useRouter();
  const [fields, setFields] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [problems, setProblems] = useState<SyncProblem[] | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body: Record<string, string> = {
      email: String(f.get("email") ?? ""),
      first_name: String(f.get("first_name") ?? ""),
      last_name: String(f.get("last_name") ?? ""),
      password: String(f.get("password") ?? ""),
    };
    const phone = String(f.get("phone_number") ?? "").trim();
    if (phone) body.phone_number = phone;

    setLoading(true);
    setFields({});
    setGeneral(undefined);
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const parsed = parseFormErrors(data);
        setFields(parsed.fields);
        setGeneral(parsed.general);
        return;
      }
      if (!data?.authenticated) {
        router.push(`/login?next=${encodeURIComponent(next)}`);
        return;
      }
      const result = await completeAuth();
      if (result.problems.length) {
        setProblems(result.problems);
        return;
      }
      router.push(next);
      router.refresh();
    } catch {
      setGeneral("Could not reach the server. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (problems) return <SyncProblems problems={problems} next={next} />;

  return (
    <form onSubmit={onSubmit} className="space-y-5" noValidate>
      <h1 className="text-2xl">Create account</h1>
      {general && (
        <p role="alert" className="text-danger">
          {general}
        </p>
      )}
      <div className="grid gap-5 sm:grid-cols-2">
        <Input label="First name" name="first_name" autoComplete="given-name" error={fields.first_name} required />
        <Input label="Last name" name="last_name" autoComplete="family-name" error={fields.last_name} required />
      </div>
      <Input label="Email" name="email" type="email" autoComplete="email" error={fields.email} required />
      <Input label="Phone (optional)" name="phone_number" type="tel" autoComplete="tel" error={fields.phone_number} />
      <Input
        label="Password"
        name="password"
        type="password"
        autoComplete="new-password"
        minLength={8}
        hint="At least 8 characters."
        error={fields.password}
        required
      />
      <Button type="submit" loading={loading} className="w-full">
        Create account
      </Button>
      <p className="text-sm">
        Already registered?{" "}
        <Link href={`/login?next=${encodeURIComponent(next)}`} className="underline">
          Log in
        </Link>
      </p>
    </form>
  );
}
