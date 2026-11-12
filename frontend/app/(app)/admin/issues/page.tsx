import type { Metadata } from "next";
import Link from "next/link";
import { Pager, Stat, one, qs } from "@/components/admin/ui";
import { PageHeader } from "@/components/PageHeader";
import { fmtUtc } from "@/lib/format";
import { serverApi, unwrap } from "@/lib/server-api";

export const metadata: Metadata = { title: "Issues" };
const STATUSES = ["open", "resolved", "ignored"] as const;
const TONE = { open: "badge-bad", resolved: "badge-ok", ignored: "badge-info" } as const;
const PAGE_SIZE = 15;

export default async function IssuesPage({ searchParams }: PageProps<"/admin/issues">) {
  const sp = await searchParams;
  const q = one(sp.q) ?? "";
  const status = STATUSES.find((s) => s === one(sp.status)) ?? (one(sp.status) === "all" ? undefined : "open");
  const page = Math.max(1, Number(one(sp.page)) || 1);

  const api = await serverApi();
  const data = unwrap(await api.GET("/api/v1/admin/issues", { params: { query: { status, q, page, page_size: PAGE_SIZE } } }));
  const href = (p: number) => `/admin/issues${qs({ q, status: status ?? "all", page: p })}`;

  return (
    <>
      <PageHeader
        crumbs={[{ label: "Students", to: "/admin" }, { label: "Issues" }]}
        eyebrow="Management"
        title="Issues"
        lede="Unhandled errors, grouped by where they happen so one bug is one row however often it fires. Each has its stack trace and the requests that hit it. A resolved issue reopens by itself if it comes back."
      />
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <Stat value={data.by_status.open ?? 0} label="Open" tone={data.by_status.open ? "bad" : undefined} />
        <Stat value={data.by_status.resolved ?? 0} label="Resolved" />
        <Stat value={data.by_status.ignored ?? 0} label="Ignored" />
      </div>
      <div className="card">
        <form method="get" className="flex flex-wrap items-center gap-3 border-b border-line-soft p-4">
          <label className="sr-only" htmlFor="q">Search issues</label>
          <input id="q" name="q" defaultValue={q} className="input !w-72" placeholder="Search error or file" />
          <label className="sr-only" htmlFor="status">Status</label>
          <select id="status" name="status" defaultValue={status ?? "all"} className="input !w-auto">
            <option value="all">All statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <button type="submit" className="btn btn-sm">Apply</button>
          <span className="ml-auto text-sm text-muted">{data.total} {data.total === 1 ? "issue" : "issues"}</span>
        </form>
        <div className="overflow-x-auto">
          <table className="table">
            <thead><tr><th>Error</th><th>Status</th><th className="num">Times</th><th>First seen (UTC)</th><th>Last seen (UTC)</th></tr></thead>
            <tbody>
              {data.items.map((i) => (
                <tr key={i.id} className="hover:bg-ink-50">
                  <td className="max-w-[520px]">
                    <Link href={`/admin/issues/${i.id}`} className="font-semibold hover:text-crimson hover:underline">{i.title}</Link>
                    <div className="text-xs text-muted">{i.culprit} · {i.source}</div>
                  </td>
                  <td><span className={`badge ${TONE[i.status]}`}>{i.status}</span></td>
                  <td className="num">{i.count}</td>
                  <td className="text-sm text-muted">{fmtUtc(i.first_seen)}</td>
                  <td className="text-sm text-muted">{fmtUtc(i.last_seen)}</td>
                </tr>
              ))}
              {!data.items.length && (
                <tr><td colSpan={5} className="empty"><h3>No issues here</h3>{status === "open" ? "Nothing is currently failing." : "Nothing matches these filters."}</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <Pager page={page} size={PAGE_SIZE} total={data.total} href={href} />
      </div>
    </>
  );
}
