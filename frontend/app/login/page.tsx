import type { Metadata } from "next";
import { LoginForm } from "@/components/auth/LoginForm";
import { safeNext } from "@/lib/auth/next";

export const metadata: Metadata = { title: "Log in" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  const { next } = await searchParams;
  return (
    <main className="container-page py-12">
      <div className="mx-auto max-w-md">
        <LoginForm next={safeNext(next)} />
      </div>
    </main>
  );
}
