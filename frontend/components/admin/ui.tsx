import Link from "next/link";

export const LEVEL_TONE: Record<string, string> = {
  INFO: "badge-info",
  WARNING: "badge-warn",
  ERROR: "badge-bad",
  CRITICAL: "badge-bad",
};
export const statusTone = (s?: number | null) =>
  !s ? "badge-info" : s >= 500 ? "badge-bad" : s >= 400 ? "badge-warn" : "badge-ok";

/** Previous / next links that keep the other filters in the URL. */
export function Pager({ page, size, total, href }: { page: number; size: number; total: number; href: (p: number) => string }) {
  const pages = Math.max(1, Math.ceil(total / size));
  if (pages <= 1) return null;
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between border-t border-line-soft px-4 py-3 text-sm">
      {page > 1 ? <Link href={href(page - 1)} className="btn btn-secondary btn-sm">← Previous</Link> : <span />}
      <span className="text-muted">Page {page} of {pages}</span>
      {page < pages ? <Link href={href(page + 1)} className="btn btn-secondary btn-sm">Next →</Link> : <span />}
    </nav>
  );
}

export function Stat({ value, label, tone }: { value: string | number; label: string; tone?: "bad" | "warn" }) {
  return (
    <div className="card card-pad">
      <div className={`font-serif text-4xl tabular-nums ${tone === "bad" ? "text-bad" : tone === "warn" ? "text-warn" : ""}`}>{value}</div>
      <div className="mt-1 text-sm text-muted">{label}</div>
    </div>
  );
}

export const one = (v: string | string[] | undefined) => (typeof v === "string" ? v : undefined);

export function qs(params: Record<string, string | number | undefined>): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "" && v !== 1) u.set(k, String(v));
  const s = u.toString();
  return s ? `?${s}` : "";
}
