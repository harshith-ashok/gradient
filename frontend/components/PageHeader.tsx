import Link from "next/link";

type Crumb = { label: string; to?: string };

export function PageHeader({
  eyebrow, title, lede, crumbs, actions,
}: {
  eyebrow?: string; title: string; lede?: string; crumbs?: Crumb[]; actions?: React.ReactNode;
}) {
  return (
    <div className="mb-8">
      {crumbs && (
        <nav aria-label="Breadcrumb" className="mb-3 flex flex-wrap gap-1.5 text-sm text-muted-foreground">
          {crumbs.map((c, i) => (
            <span key={i} className="flex gap-1.5">
              {c.to ? <Link href={c.to} className="hover:text-primary hover:underline">{c.label}</Link> : <span>{c.label}</span>}
              {i < crumbs.length - 1 && <span aria-hidden="true">/</span>}
            </span>
          ))}
        </nav>
      )}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          {eyebrow && <p className="text-xs font-medium uppercase tracking-[0.16em] text-primary">{eyebrow}</p>}
          <h1 className="mt-1.5 text-4xl font-semibold leading-tight">{title}</h1>
          {lede && <p className="mt-2 text-muted-foreground">{lede}</p>}
        </div>
        {actions && <div className="flex gap-2">{actions}</div>}
      </div>
    </div>
  );
}
