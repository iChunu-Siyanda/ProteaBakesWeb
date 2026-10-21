// Only allow same-site relative redirects (blocks //evil.com and https://...).
export function safeNext(next: string | string[] | undefined, fallback = "/"): string {
  const v = Array.isArray(next) ? next[0] : next;
  return v && v.startsWith("/") && !v.startsWith("//") ? v : fallback;
}
