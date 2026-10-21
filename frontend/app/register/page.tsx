import type { Metadata } from "next";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { safeNext } from "@/lib/auth/next";

export const metadata: Metadata = { title: "Create account" };

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  const { next } = await searchParams;
  return (
    <main className="container-page py-12">
      <div className="mx-auto max-w-md">
        <RegisterForm next={safeNext(next)} />
      </div>
    </main>
  );
}
