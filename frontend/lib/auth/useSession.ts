"use client";

import { useEffect, useState } from "react";

const EVENT = "pb:session";

/** Call after login/register/logout so the header updates. */
export function notifySessionChange() {
  window.dispatchEvent(new Event(EVENT));
}

/** null = unknown yet, true/false afterwards. */
export function useSession() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/auth/session", { cache: "no-store" })
        .then((r) => r.json())
        .then((d) => active && setAuthenticated(Boolean(d.authenticated)))
        .catch(() => active && setAuthenticated(false));
    load();
    window.addEventListener(EVENT, load);
    return () => {
      active = false;
      window.removeEventListener(EVENT, load);
    };
  }, []);

  return authenticated;
}
