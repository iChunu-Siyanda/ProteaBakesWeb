"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { completeAuth } from "@/lib/auth/afterAuth";
import type { SyncProblem } from "@/lib/cart/syncCart";
import { SyncProblems } from "./SyncProblems";

export function LoginForm({ next }: { next: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [problems, setProblems] = useState<SyncProblem[] | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        setError(data?.message ?? data?.detail ?? "Login failed. Please try again.");
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
      setError("Could not reach the server. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (problems) return <SyncProblems problems={problems} next={next} />;

  return (
    <form onSubmit={onSubmit} className="space-y-5" noValidate>
      <h1 className="text-2xl">Log in</h1>
      {error && (
        <p role="alert" className="text-danger">
          {error}
        </p>
      )}
      <Input label="Email" name="email" type="email" autoComplete="email" required />
      <Input label="Password" name="password" type="password" autoComplete="current-password" required />
      <Button type="submit" loading={loading} className="w-full">
        Log in
      </Button>
      <p className="text-sm">
        New here?{" "}
        <Link href={`/register?next=${encodeURIComponent(next)}`} className="underline">
          Create an account
        </Link>
      </p>
    </form>
  );
}
