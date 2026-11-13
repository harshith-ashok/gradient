import Link from "next/link";
import type { BadgeTone } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export const LEVEL_TONE: Record<string, BadgeTone> = {
  INFO: "secondary",
  WARNING: "warning",
  ERROR: "destructive",
  CRITICAL: "destructive",
};
export const statusTone = (s?: number | null): BadgeTone =>
  !s ? "secondary" : s >= 500 ? "destructive" : s >= 400 ? "warning" : "success";

/** Previous / next links that keep the other filters in the URL. */
export function Pager({ page, size, total, href }: { page: number; size: number; total: number; href: (p: number) => string }) {
  const pages = Math.max(1, Math.ceil(total / size));
  if (pages <= 1) return null;
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between border-t border-border px-4 py-3 text-sm">
      {page > 1 ? <Link href={href(page - 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>← Previous</Link> : <span />}
      <span className="text-muted-foreground">Page {page} of {pages}</span>
      {page < pages ? <Link href={href(page + 1)} className={buttonVariants({ variant: "outline", size: "sm" })}>Next →</Link> : <span />}
    </nav>
  );
}

export function Stat({ value, label, tone }: { value: string | number; label: string; tone?: "bad" | "warn" }) {
  return (
    <Card className="gap-0 p-6">
      <div className={` text-4xl font-semibold tabular-nums ${tone === "bad" ? "text-destructive" : tone === "warn" ? "text-warning" : ""}`}>{value}</div>
      <div className="mt-1 text-sm text-muted-foreground">{label}</div>
    </Card>
  );
}

export const one = (v: string | string[] | undefined) => (typeof v === "string" ? v : undefined);

export function qs(params: Record<string, string | number | undefined>): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "" && v !== 1) u.set(k, String(v));
  const s = u.toString();
  return s ? `?${s}` : "";
}
