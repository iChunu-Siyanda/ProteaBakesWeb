"use client";

import { useRouter } from "next/navigation";
import { Button, ButtonLink } from "@/components/ui/Button";
import { notifySessionChange, useSession } from "@/lib/auth/useSession";
import { resetServerCart } from "@/lib/cart/useServerCart";

export function AuthLinks() {
  const router = useRouter();
  const session = useSession();

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => null);
    resetServerCart();
    notifySessionChange();
    router.push("/");
    router.refresh();
  }

  if (session === null) return null; // avoids a flash of the wrong state

  return session ? (
    <Button variant="ghost" onClick={logout}>
      Log out
    </Button>
  ) : (
    <>
      <ButtonLink href="/login" variant="ghost">
        Log in
      </ButtonLink>
      <ButtonLink href="/register" variant="outline">
        Sign up
      </ButtonLink>
    </>
  );
}
